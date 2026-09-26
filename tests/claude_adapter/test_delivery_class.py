"""ga-fsfg R3: the `delivery` class pushes, opens and merges a signed Operations branch.

The gate runs in-process so its Git and gh reads can use an offline transport: a
local bare repository answers `ls-remote origin` and a fixture answers `gh`. Every
other read, and every signature check, runs the real `/usr/bin/git` and
`/usr/bin/gpg`. Commits carry genuine OpenPGP signatures (see openpgp_signer.py).
"""

from __future__ import annotations

import hashlib
import inspect
import io
import json
import os
import shlex
import subprocess
import sys
import time
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from aegis_foundation.gate.hooks import (
    contracts,
    delivery,
    delivery_binding,
    delivery_checks,
    delivery_worktree,
    payloads,
    shell_policy,
    tracking,
)
from aegis_foundation.gate.hooks.contracts import AEGIS_DEGRADED_EVENTS_REL, Payload
from aegis_foundation.gate.hooks.pretool import pretooluse_gate_with_degraded_fallback
from openpgp_signer import SigningKey, install_public_key, signed_commit_object
from test_native_command_profile import CONTEXT_REL, PROFILE, WORKFLOW_REL, git
from test_pretooluse_gates import (
    POSTTOOLUSE,
    PRETOOLUSE,
    REPO_ROOT,
    read_gate_decisions,
    run,
    run_gate,
    write,
)
from test_stationary_orchestrator import registered_fixture, stationary_fixture

REPOSITORY = "example/fixture-project"
REMOTE_URL = "git@github.com:example/fixture-project.git"
DELIVERY_PATH = "/usr/local/bin:/usr/bin:/bin"
BRANCH = "codex/ga-one-beads-first-guidance"
REQUIRED = ["ci / test"]
HELPERS = [
    {"key": "credential.https://github.com.helper", "value": ""},
    {"key": "credential.https://github.com.helper", "value": "!/usr/bin/gh auth git-credential"},
    {"key": "credential.https://gist.github.com.helper", "value": ""},
    {
        "key": "credential.https://gist.github.com.helper",
        "value": "!/usr/bin/gh auth git-credential",
    },
]
GLOBAL_CONFIG = (
    '[credential "https://github.com"]\n'
    "\thelper =\n"
    "\thelper = !/usr/bin/gh auth git-credential\n"
    '[credential "https://gist.github.com"]\n'
    "\thelper =\n"
    "\thelper = !/usr/bin/gh auth git-credential\n"
    '[filter "lfs"]\n'
    "\tclean = git-lfs clean -- %f\n"
    "\tsmudge = git-lfs smudge -- %f\n"
    "\tprocess = git-lfs filter-process\n"
    "\trequired = true\n"
    "[push]\n"
    "\tautoSetupRemote = true\n"
)
SSH_SIGNATURE = "-----BEGIN SSH SIGNATURE-----\nU1NIU0lHAAAAAQ==\n-----END SSH SIGNATURE-----\n"
X509_SIGNATURE = "-----BEGIN SIGNED MESSAGE-----\nMIAGCSqGSIb3DQ==\n-----END SIGNED MESSAGE-----\n"
OPERATIONS = ["push", "pr-create", "pr-merge"]
UNTRUSTED = "__aegis_untrusted_environment__"


@dataclass
class Outcome:
    code: int
    out: str
    err: str

    @property
    def approved(self) -> bool:
        if self.code != 0 or not self.out.strip():
            return False
        decision = json.loads(self.out)["hookSpecificOutput"]
        return (
            decision["permissionDecision"] == "allow"
            and decision["permissionDecisionReason"] == "aegis-orchestrator:delivery"
        )

    @property
    def refused(self) -> bool:
        return self.code == 2 and '"permissionDecision": "allow"' not in self.out


class Transport:
    """Offline stand-in for the network: ls-remote reads the bare repo, gh is a fixture."""

    def __init__(self, bare: Path, tmpdir: Path) -> None:
        self.bare = bare
        self.tmpdir = tmpdir
        self.calls: list[tuple[list[str], dict]] = []
        self.pr: dict | None = None
        self.socket = {"http_unix_socket": b"", "github.com": b""}
        self.real = subprocess.run

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), dict(kwargs)))
        if argv[0] == "/usr/bin/gh":
            if list(argv[1:3]) == ["config", "get"]:
                scope = "github.com" if "-h" in argv else "http_unix_socket"
                return subprocess.CompletedProcess(argv, 0, self.socket[scope], b"")
            if list(argv[1:3]) == ["pr", "view"] and self.pr is not None:
                return subprocess.CompletedProcess(argv, 0, json.dumps(self.pr).encode(), b"")
            return subprocess.CompletedProcess(argv, 1, b"", b"unexpected gh call")
        argv = list(argv)
        if "ls-remote" in argv and argv[argv.index("ls-remote") + 1] == "origin":
            argv[argv.index("ls-remote") + 1] = str(self.bare)
        # git writes the signature it verifies to $TMPDIR, else /tmp, which a sandboxed
        # test run cannot write. The gate itself passes no TMPDIR.
        env = {**(kwargs.get("env") or {}), "TMPDIR": str(self.tmpdir)}
        return self.real(argv, **{**kwargs, "env": env})


@dataclass
class Lane:
    canonical: Path
    worktree: Path
    journal: Path
    bare: Path
    home: Path
    key: SigningKey
    foreign: SigningKey
    transport: Transport
    monkeypatch: pytest.MonkeyPatch
    capsys: pytest.CaptureFixture
    tmp_path: Path
    extra: dict = field(default_factory=dict)
    calls: int = 0

    @property
    def body(self) -> Path:
        return self.worktree / "docs/pr-body.md"

    @property
    def admin(self) -> Path:
        return self.canonical / ".git/worktrees" / self.worktree.name

    def head(self) -> str:
        return run(["git", "rev-parse", "HEAD"], self.worktree).stdout.strip()

    def profile(self) -> dict:
        return json.loads((self.canonical / PROFILE).read_text())

    def write_profile(self, value: dict) -> None:
        """Commit a new canonical profile and rebuild the branch on top of it."""

        write(self.canonical / PROFILE, json.dumps(value))
        git(self.canonical, "commit", "-qam", "profile change")
        git(self.worktree, "reset", "-q", "--hard", "main")
        git(self.canonical, "push", "-q", "--force", str(self.bare), "main")
        self.commit("docs: add the pull request body", {"docs/pr-body.md": "Signed delivery.\n"})

    def set_profile(self, **changes) -> None:
        value = self.profile()
        value.update(changes)
        self.write_profile(value)

    def commit_index(
        self,
        message: str,
        *,
        key: SigningKey | None = None,
        signature: str | None = None,
        sign: bool = True,
    ) -> str:
        tree = run(["git", "write-tree"], self.worktree).stdout.strip()
        unsigned = run(["git", "commit-tree", tree, "-p", "HEAD", "-m", message], self.worktree)
        oid = unsigned.stdout.strip()
        if sign or signature is not None:
            raw = subprocess.run(
                ["git", "cat-file", "commit", oid], cwd=self.worktree, capture_output=True
            ).stdout
            text = signature if signature is not None else (key or self.key).sign(raw)
            written = subprocess.run(
                ["git", "hash-object", "-t", "commit", "-w", "--stdin"],
                cwd=self.worktree,
                input=signed_commit_object(raw, text),
                capture_output=True,
            )
            oid = written.stdout.decode().strip()
        git(self.worktree, "update-ref", "HEAD", oid)
        return oid

    def commit(self, message: str, files: dict[str, str], **options) -> str:
        for relative, text in files.items():
            write(self.worktree / relative, text)
        git(self.worktree, "add", *files)
        return self.commit_index(message, **options)

    def publish(self, ref: str = "HEAD") -> None:
        git(self.worktree, "push", "-q", "--force", str(self.bare), f"{ref}:refs/heads/{BRANCH}")

    def pull_request(self, **changes) -> dict:
        view = {
            "state": "OPEN",
            "baseRefName": "main",
            "headRefName": BRANCH,
            "headRefOid": self.head(),
            "isCrossRepository": False,
            "statusCheckRollup": [
                {
                    "__typename": "CheckRun",
                    "name": "ci / test",
                    "status": "COMPLETED",
                    "conclusion": "SUCCESS",
                },
                {"__typename": "StatusContext", "context": "lint", "state": "SUCCESS"},
            ],
        }
        view.update(changes)
        self.transport.pr = view
        return view

    def prefix(self) -> list[str]:
        value = self.profile()
        return ["/usr/bin/env", "-i", f"HOME={value['delivery_home']}", f"PATH={value['delivery_path']}"]

    def push(self, worktree: Path | str | None = None, branch: str = BRANCH) -> str:
        words = ["/usr/bin/git", "-C", str(worktree or self.worktree), "push", "origin", branch]
        return shlex.join([*self.prefix(), *words])

    def create(self, body: Path | str | None = None, branch: str = BRANCH, title: str = "") -> str:
        words = [
            "/usr/bin/gh",
            "pr",
            "create",
            "--repo",
            f"github.com/{REPOSITORY}",
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            title or "Deliver the signed branch",
            "--body-file",
            str(body or self.body),
        ]
        return shlex.join([*self.prefix(), *words])

    def merge(self, number: str = "7", sha: str | None = None) -> str:
        words = [
            "/usr/bin/gh",
            "pr",
            "merge",
            number,
            "--repo",
            f"github.com/{REPOSITORY}",
            "--merge",
            "--match-head-commit",
            sha or self.head(),
        ]
        return shlex.join([*self.prefix(), *words])

    def command(self, operation: str) -> str:
        """A valid command for the operation, with its remote state prepared."""

        if operation == "push":
            return self.push()
        self.publish()
        if operation == "pr-create":
            return self.create()
        self.pull_request()
        return self.merge()

    def payload(self, command: str, *, tool_use_id: str | None = None, **overrides) -> dict:
        self.calls += 1
        value = {
            "hook_event_name": "PreToolUse",
            "session_id": "synthetic-session",
            "tool_use_id": tool_use_id or f"toolu_{self.calls:04d}",
            "cwd": str(self.canonical),
            "permission_mode": "dontAsk",
            "tool_name": "Bash",
            "tool_input": {"command": command, "description": "Deliver"},
        }
        value.update(overrides)
        return value

    def _environment(self) -> None:
        self.monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(self.canonical))
        self.monkeypatch.setenv("AEGIS_INVOKING_AGENT", "claude")

    def pre(self, payload: dict) -> Outcome:
        self._environment()
        self.capsys.readouterr()
        code = pretooluse_gate_with_degraded_fallback(json.dumps(payload))
        captured = self.capsys.readouterr()
        return Outcome(code, captured.out, captured.err)

    def post(self, payload: dict) -> Outcome:
        self._environment()
        event = {
            **payload,
            "hook_event_name": "PostToolUse",
            "tool_response": {"stdout": "", "stderr": "", "interrupted": False},
        }
        self.monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
        self.capsys.readouterr()
        code = tracking.posttooluse_tracking()
        captured = self.capsys.readouterr()
        return Outcome(code, captured.out, captured.err)

    def failed(self, payload: dict) -> Outcome:
        self._environment()
        event = {**payload, "hook_event_name": "PostToolUseFailure", "error": "exit status 1"}
        self.monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
        self.capsys.readouterr()
        code = delivery.delivery_failure()
        captured = self.capsys.readouterr()
        return Outcome(code, captured.out, captured.err)

    def events(self, root: Path | None = None) -> list[dict]:
        path = (root or self.worktree) / ".aegis/state/pending-tracking.json"
        return json.loads(path.read_text())["events"] if path.exists() else []

    def bindings(self) -> list[Path]:
        directory = self.canonical / ".aegis/state/delivery-bindings"
        return sorted(directory.iterdir()) if directory.is_dir() else []


def current_work(worktree: Path, mode: str = "bead") -> str:
    return json.dumps(
        {
            "schema_version": "1.0.0",
            "mode": mode,
            "status": "in-progress",
            "task": {
                "id": "ga-one",
                "slug": "beads-first-guidance",
                "source": "gas-city-bead",
                "status": "in-progress",
            },
            "branch": {"current": BRANCH},
            "paths": {
                "session": (worktree / "sessions/current").resolve().relative_to(worktree).as_posix(),
                "plan": (worktree / "plans/current").resolve().relative_to(worktree).as_posix(),
            },
        }
    )


def build_lane(tmp_path, monkeypatch, capsys, *, registered: bool = False) -> Lane:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-config"))
    monkeypatch.delenv("AEGIS_INVOKING_AGENT", raising=False)
    extra: dict = {}
    if registered:
        canonical, worktree, core, core_target, _ = registered_fixture(tmp_path)
        extra.update(core=core, core_target=core_target)
        journal = canonical / ".git/gas-city-workflow/transactions/ga-one.json"
    else:
        canonical, worktree, journal = stationary_fixture(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    write(home / ".gitconfig", GLOBAL_CONFIG)
    key = SigningKey("Fixture Signer <signer@example.invalid>")
    foreign = SigningKey("Foreign Signer <foreign@example.invalid>")
    install_public_key(home, key)
    install_public_key(home, foreign)
    value = json.loads((canonical / PROFILE).read_text())
    value["commands"].append("delivery")
    value.update(
        repository=REPOSITORY,
        default_branch="main",
        remote_url=REMOTE_URL,
        signing_key=key.fingerprint,
        required_checks=REQUIRED,
        delivery_path=DELIVERY_PATH,
        delivery_home=str(home),
        credential_helpers=HELPERS,
    )
    write(canonical / PROFILE, json.dumps(value))
    git(canonical, "commit", "-qam", "opt in to delivery")
    git(worktree, "reset", "-q", "--hard", "main")
    bare = tmp_path / "origin.git"
    assert run(["git", "init", "-q", "--bare", str(bare)], tmp_path).returncode == 0
    git(canonical, "push", "-q", str(bare), "main")
    transport = Transport(bare, tmp_path)
    monkeypatch.setattr(
        delivery_checks,
        "subprocess",
        types.SimpleNamespace(
            run=transport,
            SubprocessError=subprocess.SubprocessError,
            TimeoutExpired=subprocess.TimeoutExpired,
        ),
    )
    write(worktree / ".aegis/state/current-work.json", current_work(worktree))
    lane = Lane(
        canonical,
        worktree,
        journal,
        bare,
        home,
        key,
        foreign,
        transport,
        monkeypatch,
        capsys,
        tmp_path,
        extra,
    )
    lane.commit("docs: add the pull request body", {"docs/pr-body.md": "Signed delivery.\n"})
    return lane


@pytest.fixture
def lane(tmp_path, monkeypatch, capsys) -> Lane:
    return build_lane(tmp_path, monkeypatch, capsys)


def replace_once(text: str, old: str, new: str) -> str:
    assert old in text, (old, text)
    return text.replace(old, new, 1)


# --- Approvals ----------------------------------------------------------------------


@pytest.mark.parametrize("operation", OPERATIONS)
def test_each_operation_is_approved_and_audited_on_the_worktree(lane, operation):
    result = lane.pre(lane.payload(lane.command(operation)))
    assert result.approved, result.err
    assert read_gate_decisions(lane.worktree)[-1]["reason"] == "native_permission:delivery"
    assert not read_gate_decisions(lane.canonical)
    # Exactly one binding names the worktree and the operation; its name is a digest.
    [binding] = lane.bindings()
    record = json.loads(binding.read_text())
    assert record["worktree"] == str(lane.worktree) and record["operation"] == operation
    assert len(binding.stem) == 64 and "synthetic-session" not in binding.read_text()


def test_the_approval_does_not_touch_the_canonical_checkout(lane):
    before = run(["git", "status", "--porcelain"], lane.canonical).stdout
    assert lane.pre(lane.payload(lane.command("push"))).approved
    assert run(["git", "status", "--porcelain"], lane.canonical).stdout == before
    assert run(["git", "branch", "--show-current"], lane.canonical).stdout.strip() == "main"


def test_every_delivery_read_carries_the_fixed_environment_and_hardening(lane):
    lane.transport.calls.clear()
    assert lane.pre(lane.payload(lane.command("pr-merge"))).approved
    calls = lane.transport.calls
    git_calls = [(argv, kwargs) for argv, kwargs in calls if argv[0] == "/usr/bin/git"]
    gh_calls = [(argv, kwargs) for argv, kwargs in calls if argv[0] == "/usr/bin/gh"]
    hardened = [*delivery_checks.GIT_BASE, *delivery_checks.GIT_HARDENING]
    reads = 0
    for argv, kwargs in git_calls:
        if argv[1] == "check-ref-format":
            continue  # the profile loader's default_branch check, not a delivery read
        reads += 1
        options = argv[1 : argv.index("-C")]
        # The configuration check alone runs without the gate's own -c entries.
        expected = delivery_checks.GIT_BASE if "--show-scope" in argv else hardened
        assert options == list(expected), argv
        assert kwargs["env"] == {
            "HOME": str(lane.home),
            "PATH": DELIVERY_PATH,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_ATTR_NOSYSTEM": "1",
        }
        assert 0 < kwargs["timeout"] <= 30
    assert reads > 20 and len(gh_calls) == 3
    for argv, kwargs in gh_calls:
        assert kwargs["env"] == {"HOME": str(lane.home), "PATH": DELIVERY_PATH}
        assert 0 < kwargs["timeout"] <= 30
        assert kwargs["cwd"] == str(lane.canonical)
    assert [argv for argv, _ in gh_calls] == [
        ["/usr/bin/gh", "config", "get", "http_unix_socket"],
        ["/usr/bin/gh", "config", "get", "-h", "github.com", "http_unix_socket"],
        [
            "/usr/bin/gh",
            "pr",
            "view",
            "7",
            "--repo",
            f"github.com/{REPOSITORY}",
            "--json",
            "state,baseRefName,headRefName,headRefOid,isCrossRepository,statusCheckRollup",
        ],
    ]


def test_the_evaluation_runs_once_per_pretooluse(lane):
    lane.transport.calls.clear()
    assert lane.pre(lane.payload(lane.command("push"))).approved
    listings = [argv for argv, _ in lane.transport.calls if "--show-scope" in argv]
    # One configuration read for <W> and one for the canonical root, not two of each.
    assert len(listings) == 2


# --- The closed grammar -------------------------------------------------------------


PREFIX_DEFECTS = {
    "no-prefix": lambda lane, command: shlex.join(shlex.split(command)[4:]),
    "bare-env": lambda lane, command: replace_once(command, "/usr/bin/env -i", "env -i"),
    "assignments-only": lambda lane, command: shlex.join(shlex.split(command)[2:]),
    "env-without-i": lambda lane, command: shlex.join(
        ["/usr/bin/env", *shlex.split(command)[2:]]
    ),
    "other-home": lambda lane, command: replace_once(command, f"HOME={lane.home}", "HOME=/tmp"),
    "other-path": lambda lane, command: replace_once(
        command, f"PATH={DELIVERY_PATH}", "PATH=/usr/bin:/bin"
    ),
    "extra-assignment": lambda lane, command: replace_once(
        command, f"PATH={DELIVERY_PATH}", f"PATH={DELIVERY_PATH} GIT_DIR=/tmp/elsewhere"
    ),
    "leading-assignment": lambda lane, command: "GIT_DIR=/tmp/x " + command,
    "reordered": lambda lane, command: shlex.join(
        [*shlex.split(command)[:2], shlex.split(command)[3], shlex.split(command)[2]]
        + shlex.split(command)[4:]
    ),
    "unset-option": lambda lane, command: replace_once(
        command, "/usr/bin/env -i", "/usr/bin/env -i -u GIT_DIR"
    ),
    "wrapper": lambda lane, command: "/usr/bin/nice " + command,
    # The same words, quoted differently from shlex.join: not the canonical rendering.
    "double-quoted": lambda lane, command: (
        replace_once(command, " origin ", ' "origin" ')
        if " origin " in command
        else replace_once(command, f"github.com/{REPOSITORY}", f'"github.com/{REPOSITORY}"')
    ),
}


@pytest.mark.parametrize("defect", sorted(PREFIX_DEFECTS))
@pytest.mark.parametrize("operation", OPERATIONS)
def test_only_the_exact_fixed_environment_prefix_is_accepted(lane, operation, defect):
    command = PREFIX_DEFECTS[defect](lane, lane.command(operation))
    result = lane.pre(lane.payload(command))
    assert result.refused, (command, result.out)
    assert not lane.bindings()


@pytest.mark.parametrize(
    "option",
    [
        ["-c", "core.sshCommand=/bin/sh"],
        ["--config-env=core.askPass=ASKPASS"],
        ["--exec-path=/tmp"],
        ["--git-dir=/tmp/elsewhere"],
        ["--work-tree=/tmp"],
        ["--namespace=other"],
        ["--no-replace-objects"],
        ["-C", "/tmp"],
    ],
)
@pytest.mark.parametrize("position", ["before-C", "before-push"])
def test_no_git_global_option_but_C_is_accepted(lane, option, position):
    words = ["/usr/bin/git", "-C", str(lane.worktree), "push", "origin", BRANCH]
    index = 1 if position == "before-C" else 3
    command = shlex.join([*lane.prefix(), *words[:index], *option, *words[index:]])
    assert lane.pre(lane.payload(command)).refused


@pytest.mark.parametrize(
    "tail",
    [
        ["push", "--force", "origin", BRANCH],
        ["push", "-f", "origin", BRANCH],
        ["push", "origin", BRANCH, "--force"],
        ["push", "--force-with-lease", "origin", BRANCH],
        ["push", "--delete", "origin", BRANCH],
        ["push", "-d", "origin", BRANCH],
        ["push", "--mirror", "origin"],
        ["push", "--all", "origin"],
        ["push", "--tags", "origin", BRANCH],
        ["push", "--prune", "origin", BRANCH],
        ["push", "-o", "ci.skip", "origin", BRANCH],
        ["push", "--push-option=ci.skip", "origin", BRANCH],
        ["push", "--receive-pack=/bin/sh", "origin", BRANCH],
        ["push", "--exec=/bin/sh", "origin", BRANCH],
        ["push", "--no-verify", "origin", BRANCH],
        ["push", "-u", "origin", BRANCH],
        ["push", "origin", f"+{BRANCH}"],
        ["push", "origin", f"{BRANCH}:main"],
        ["push", "origin", f":{BRANCH}"],
        ["push", "origin", "HEAD"],
        ["push", "origin"],
        ["push", "origin", BRANCH, "main"],
        ["push", "upstream", BRANCH],
        ["push", "https://github.com/example/fixture-project.git", BRANCH],
        ["push", "/tmp/elsewhere.git", BRANCH],
        ["push", "origin", "-" + BRANCH],
        ["push", "origin", "refs/heads/" + BRANCH],
        ["push", "origin", "heads/" + BRANCH],
        ["push", "origin", "main"],
        ["push", "origin", "FETCH_HEAD"],
        ["push", "origin", "codex/ga-one-HEAD"],
    ],
)
def test_push_takes_exactly_origin_and_a_plain_branch(lane, tail):
    command = shlex.join([*lane.prefix(), "/usr/bin/git", "-C", str(lane.worktree), *tail])
    result = lane.pre(lane.payload(command))
    assert result.refused
    if "--force" in tail or "-f" in tail:
        # Hard policy keeps its precedence over every class.
        assert read_gate_decisions(lane.canonical)[-1]["reason"] == "destructive_git_operation"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda words: [*words, "--draft"],
        lambda words: [*words, "--web"],
        lambda words: [*words[:-2], "--body", "text"],
        lambda words: [*words[:3], *words[5:]],  # no --repo
        lambda words: [*words[:3], "-R", *words[4:]],
        lambda words: [*words[:4], "github.com/example/other", *words[5:]],
        lambda words: [*words[:6], "develop", *words[7:]],
        lambda words: [*words[:9], *words[11:], *words[9:11]],  # --title after --body-file
        lambda words: [*words[:10], "-draft", *words[11:]],
        lambda words: [*words[:10], "", *words[11:]],
        lambda words: [*words[:12], "docs/pr-body.md"],  # a relative body file
        lambda words: [*words[:8], "-" + BRANCH, *words[9:]],
        lambda words: [*words[:8], "main", *words[9:]],
    ],
)
def test_pr_create_takes_its_flags_in_fixed_positions_only(lane, mutate):
    words = shlex.split(lane.command("pr-create"))[4:]
    command = shlex.join([*lane.prefix(), *mutate(words)])
    assert lane.pre(lane.payload(command)).refused


@pytest.mark.parametrize(
    "mutate",
    [
        lambda words: [*words, "--admin"],
        lambda words: [*words, "--delete-branch"],
        lambda words: [*words, "-d"],
        lambda words: [*words, "--auto"],
        lambda words: [*words[:6], "--squash", *words[7:]],
        lambda words: [*words[:6], "--rebase", *words[7:]],
        lambda words: [*words[:7]],
        lambda words: [*words[:3], "7a", *words[4:]],
        lambda words: [*words[:3], "07", *words[4:]],
        lambda words: [*words[:3], "-7", *words[4:]],
        lambda words: [*words[:3], "٧", *words[4:]],
        lambda words: [*words[:3], BRANCH, *words[4:]],
        lambda words: [*words[:8], words[8].upper()],
        lambda words: [*words[:8], words[8][:39]],
        lambda words: [*words[:8], words[8] + "0"],
        lambda words: [*words[:8], "HEAD"],
    ],
)
def test_pr_merge_takes_digits_a_full_sha_and_no_other_option(lane, mutate):
    words = shlex.split(lane.command("pr-merge"))[4:]
    command = shlex.join([*lane.prefix(), *mutate(words)])
    assert lane.pre(lane.payload(command)).refused


@pytest.mark.parametrize(
    "suffix",
    ["; touch marker", " && touch marker", " | cat", " > marker", "\ntouch marker", " &"],
)
@pytest.mark.parametrize("operation", OPERATIONS)
def test_shell_syntax_refuses(lane, operation, suffix):
    assert lane.pre(lane.payload(lane.command(operation) + suffix)).refused


@pytest.mark.parametrize("title", ["$(id)", "`id`", "a;b", "x > y", "tab\there"])
def test_a_title_carrying_shell_syntax_refuses(lane, title):
    lane.publish()
    assert lane.pre(lane.payload(lane.create(title=title))).refused


def test_a_title_with_ordinary_punctuation_is_quoted_canonically(lane):
    lane.publish()
    command = lane.create(title="feat(delivery): ship [R3] * now?")
    assert "'feat(delivery): ship [R3] * now?'" in command
    assert lane.pre(lane.payload(command)).approved


# --- Worktree scope ---------------------------------------------------------------


@pytest.mark.parametrize("kind", ["registered", "review"])
def test_core_and_review_project_worktrees_refuse(tmp_path, monkeypatch, capsys, kind):
    lane = build_lane(tmp_path, monkeypatch, capsys, registered=True)
    if kind == "review":
        value = lane.profile()
        value["review_projects"] = value.pop("registered_projects")
        lane.write_profile(value)
    core_target = lane.extra["core_target"]
    core_branch = "codex/ga-core-beads-first-guidance"
    assert lane.pre(lane.payload(lane.command("push"))).approved  # control: Operations W
    assert lane.pre(lane.payload(lane.push(core_target, core_branch))).refused
    create = lane.create(body=core_target / "README.md", branch=core_branch)
    assert lane.pre(lane.payload(create)).refused
    core_head = run(["git", "rev-parse", "HEAD"], core_target).stdout.strip()
    lane.pull_request(headRefName=core_branch, headRefOid=core_head)
    assert lane.pre(lane.payload(lane.merge(sha=core_head))).refused


@pytest.mark.parametrize(
    "defect", ["outside-root", "not-linked", "other-repository", "symlink", "canonical", "nested"]
)
def test_an_unregistered_or_aliased_worktree_refuses(lane, defect):
    root = lane.worktree.parent
    branch = BRANCH
    if defect == "outside-root":
        target = lane.tmp_path / "elsewhere" / "ga-one-elsewhere"
        branch = "codex/ga-one-elsewhere"
        git(lane.canonical, "worktree", "add", "-q", "-b", branch, str(target), "main")
    elif defect == "not-linked":
        target = root / "ga-plain"
        target.mkdir()
        run(["git", "init", "-q", "-b", branch], target)
    elif defect == "other-repository":
        other = lane.tmp_path / "other-repo"
        other.mkdir()
        run(["git", "init", "-q", "-b", "main"], other)
        write(other / "README.md", "other\n")
        git(other, "add", ".")
        git(other, "commit", "-qm", "other")
        target = root / "ga-other-repository"
        git(other, "worktree", "add", "-q", "-b", branch, str(target))
    elif defect == "symlink":
        target = root / "alias"
        target.symlink_to(lane.worktree, target_is_directory=True)
    elif defect == "canonical":
        target = lane.canonical
    else:
        target = lane.worktree / "docs"
    assert lane.pre(lane.payload(lane.push(target, branch))).refused
    assert not lane.bindings()


@pytest.mark.parametrize("defect", ["not-owned", "not-ready", "branch-form"])
@pytest.mark.parametrize("operation", OPERATIONS)
def test_a_worktree_failing_coordinate_target_validation_refuses(lane, operation, defect):
    journal = json.loads(lane.journal.read_text())
    if defect == "not-owned":
        journal["external_ownership"]["ga-one"]["binding"] = "external-coordinator.v1:forged"
    elif defect == "not-ready":
        journal["phase"] = "prepared"
    lane.journal.write_text(json.dumps(journal))
    branch = BRANCH
    if defect == "branch-form":
        branch = "feature/ga-one"
        git(lane.worktree, "checkout", "-q", "-b", branch)
    if operation == "push":
        command = lane.push(branch=branch)
    elif operation == "pr-create":
        git(lane.worktree, "push", "-q", "--force", str(lane.bare), f"HEAD:refs/heads/{branch}")
        command = lane.create(branch=branch)
    else:
        lane.pull_request(headRefName=branch)
        command = lane.merge()
    assert lane.pre(lane.payload(command)).refused


def test_two_worktrees_on_one_branch_or_commit_refuse(lane):
    # A forged second gitfile naming the same private directory matches the branch too.
    twin = lane.worktree.parent / "ga-twin"
    twin.mkdir()
    (twin / ".git").write_text((lane.worktree / ".git").read_text())
    lane.publish()
    assert lane.pre(lane.payload(lane.create())).refused
    (twin / ".git").unlink()
    twin.rmdir()
    # Two real branch checkouts at the merged commit make the merge target ambiguous.
    other = lane.worktree.parent / "ga-two-same-commit"
    git(lane.canonical, "worktree", "add", "-q", "-b", "codex/ga-two-same", str(other), lane.head())
    lane.pull_request()
    assert lane.pre(lane.payload(lane.merge())).refused


def test_a_reftable_store_refuses_the_merge_lookup(lane):
    lane.publish()
    lane.pull_request()
    (lane.canonical / ".git/reftable").mkdir()
    assert lane.pre(lane.payload(lane.merge())).refused


# --- Signatures and history ---------------------------------------------------------


def _sign_defect(lane: Lane, defect: str) -> None:
    files = {f"src/{defect}.txt": f"{defect}\n"}
    if defect == "unsigned":
        lane.commit("feat: unsigned", files, sign=False)
    elif defect == "foreign-signed":
        lane.commit("feat: foreign", files, key=lane.foreign)
    elif defect == "ssh-signed":
        lane.commit("feat: ssh", files, signature=SSH_SIGNATURE)
    elif defect == "x509-signed":
        lane.commit("feat: x509", files, signature=X509_SIGNATURE)
    elif defect == "bad-signature":
        lane.commit("feat: bad", files, signature=lane.key.sign(b"some other payload"))
    elif defect == "untrusted-key":
        stranger = SigningKey("Stranger <stranger@example.invalid>")
        install_public_key(lane.home, stranger, trusted=False)
        lane.commit("feat: untrusted", files, key=stranger)
    else:  # an unsigned commit anywhere in the range, below good ones
        lane.commit("feat: unsigned middle", files, sign=False)
        lane.commit("feat: signed after", {"src/after.txt": "after\n"})


@pytest.mark.parametrize(
    "defect",
    [
        "unsigned",
        "foreign-signed",
        "ssh-signed",
        "x509-signed",
        "bad-signature",
        "untrusted-key",
        "unsigned-in-the-middle",
    ],
)
@pytest.mark.parametrize("operation", OPERATIONS)
def test_every_commit_since_remote_main_is_good_signed_by_the_profile_key(
    lane, operation, defect
):
    _sign_defect(lane, defect)
    result = lane.pre(lane.payload(lane.command(operation)))
    assert result.refused, result.err
    assert "signature" in result.err or "signed" in result.err


def _forge_commit_graph(common: Path, commit: str, parent: str) -> None:
    graph = common / "objects/info/commit-graph"
    data = bytearray(graph.read_bytes())
    assert data[:4] == b"CGPH"
    offsets = {}
    for index in range(data[6] + 1):
        entry = data[8 + index * 12 : 8 + (index + 1) * 12]
        offsets[bytes(entry[:4])] = int.from_bytes(entry[4:], "big")
    lookup, commits = offsets[b"OIDL"], offsets[b"CDAT"]
    oids = [bytes(data[lookup + i * 20 : lookup + (i + 1) * 20]).hex() for i in range((commits - lookup) // 20)]
    entry = commits + oids.index(commit) * 36
    data[entry + 20 : entry + 24] = oids.index(parent).to_bytes(4, "big")
    graph.chmod(0o644)
    graph.write_bytes(bytes(data))


@pytest.mark.parametrize("operation", OPERATIONS)
def test_a_forged_commit_graph_cannot_hide_an_unsigned_commit(lane, operation):
    main = run(["git", "rev-parse", "main"], lane.canonical).stdout.strip()
    lane.commit("feat: unsigned", {"src/unsigned.txt": "u\n"}, sign=False)
    middle = lane.commit("feat: signed middle", {"src/middle.txt": "m\n"})
    lane.commit("feat: signed tip", {"src/tip.txt": "t\n"})
    body = lane.commit("docs: body again", {"docs/pr-body.md": "Signed delivery, again.\n"})
    command = lane.command(operation)  # publish before the graph misleads Git itself
    # The graph claims the signed chain sits directly on main.
    git(lane.worktree, "commit-graph", "write", "--reachable")
    _forge_commit_graph(lane.canonical / ".git", middle, main)
    listed = run(["git", "rev-list", f"{main}..HEAD"], lane.worktree).stdout.split()
    assert len(listed) == 3 and body in listed  # the forged graph hides two commits
    result = lane.pre(lane.payload(command))
    assert result.refused and "carries no OpenPGP signature" in result.err


@pytest.mark.parametrize("defect", ["packed-replace-ref", "grafts", "shallow"])
@pytest.mark.parametrize("operation", OPERATIONS)
def test_nothing_may_rewrite_history_for_the_walk(lane, operation, defect):
    command = lane.command(operation)
    common = lane.canonical / ".git"
    if defect == "packed-replace-ref":
        main = run(["git", "rev-parse", "main"], lane.canonical).stdout.strip()
        git(lane.canonical, "replace", main, lane.head())
        git(lane.canonical, "pack-refs", "--all")
        assert not list((common / "refs/replace").glob("*"))
        assert "refs/replace/" in (common / "packed-refs").read_text()
    elif defect == "grafts":
        write(common / "info/grafts", "")
    else:
        write(common / "shallow", "")
    assert lane.pre(lane.payload(command)).refused


@pytest.mark.parametrize("defect", ["main-moved", "main-object-missing", "main-missing", "two-lines"])
@pytest.mark.parametrize("operation", OPERATIONS)
def test_remote_main_must_be_one_local_ancestor_of_head(lane, operation, defect):
    main = run(["git", "rev-parse", "main"], lane.canonical).stdout.strip()
    if defect == "main-moved":
        tree = run(["git", "rev-parse", f"{main}^{{tree}}"], lane.canonical).stdout.strip()
        newer = run(["git", "commit-tree", tree, "-p", main, "-m", "later work"], lane.canonical)
        git(lane.canonical, "push", "-q", "--force", str(lane.bare), f"{newer.stdout.strip()}:refs/heads/main")
    elif defect == "main-object-missing":
        clone = lane.tmp_path / "clone"
        assert run(["git", "clone", "-q", str(lane.bare), str(clone)], lane.tmp_path).returncode == 0
        write(clone / "later.txt", "later\n")
        git(clone, "add", ".")
        git(clone, "commit", "-qm", "later work elsewhere")
        git(clone, "push", "-q", "origin", "HEAD:refs/heads/main")
    elif defect == "main-missing":
        git(lane.bare, "update-ref", "-d", "refs/heads/main")
    else:
        git(lane.bare, "update-ref", "refs/pull/1/refs/heads/main", main)
    assert lane.pre(lane.payload(lane.command(operation))).refused


# --- The tracked tree ---------------------------------------------------------------


@pytest.mark.parametrize(
    "defect", ["modified", "staged", "assume-unchanged", "skip-worktree", "deleted"]
)
@pytest.mark.parametrize("operation", OPERATIONS)
def test_the_tracked_tree_must_be_clean_and_match_head(lane, operation, defect):
    command = lane.command(operation)
    target = lane.body
    if defect == "modified":
        write(target, "changed\n")
    elif defect == "staged":
        write(target, "staged\n")
        git(lane.worktree, "add", "docs/pr-body.md")
    elif defect == "deleted":
        target.unlink()
    else:
        flag = "--assume-unchanged" if defect == "assume-unchanged" else "--skip-worktree"
        git(lane.worktree, "update-index", flag, "docs/pr-body.md")
        write(target, "hidden change\n")
        assert run(["git", "status", "--porcelain"], lane.worktree).stdout == ""
    assert lane.pre(lane.payload(command)).refused


def test_untracked_files_do_not_make_the_tree_dirty(lane):
    write(lane.worktree / "notes/scratch.md", "untracked\n")
    assert lane.pre(lane.payload(lane.command("push"))).approved


# --- Configuration ------------------------------------------------------------------


def configure(lane: Lane, scope: str, key: str, value: str) -> None:
    if scope == "common":
        git(lane.canonical, "config", "--add", key, value)
        return
    git(lane.canonical, "config", "extensions.worktreeConfig", "true")
    root = lane.worktree if scope == "worktree" else lane.canonical
    git(root, "config", "--worktree", key, value)


@pytest.mark.parametrize(
    "key,value",
    [
        ("http.proxy", "http://127.0.0.1:9"),
        ("http.https://github.com/.extraHeader", "Authorization: x"),
        ("protocol.ext.allow", "always"),
        ("core.gitProxy", "/bin/sh"),
        ("core.fsmonitor", "/bin/sh"),
    ],
)
@pytest.mark.parametrize("scope", ["worktree", "canonical"])
@pytest.mark.parametrize("operation", OPERATIONS)
def test_network_and_monitor_keys_refuse_in_the_worktree_and_the_canonical_root(
    lane, operation, scope, key, value
):
    command = lane.command(operation)
    configure(lane, scope, key, value)
    result = lane.pre(lane.payload(command))
    assert result.refused
    assert "configuration refuses" in result.err


@pytest.mark.parametrize(
    "key,value",
    [
        ("remote.origin.pushurl", "https://example.invalid/other.git"),
        ("remote.origin.url", "https://example.invalid/second.git"),
        ("remote.origin.push", "refs/heads/*:refs/heads/*"),
        ("remote.origin.fetch", "+refs/pull/*:refs/remotes/origin/pr/*"),
        ("url.https://example.invalid/.insteadOf", "git@github.com:"),
        ("url.https://example.invalid/.pushInsteadOf", "git@github.com:"),
        ("remote.origin.mirror", "true"),
        ("remote.origin.receivepack", "/bin/sh"),
        ("remote.origin.uploadpack", "/bin/sh"),
        ("remote.origin.vcs", "sh"),
        ("remote.upstream.url", "https://example.invalid/up.git"),
        ("push.default", "current"),
        ("push.gpgSign", "true"),
        ("credential.helper", "store"),
        ("core.sshCommand", "/bin/sh"),
        ("core.askPass", "/bin/sh"),
        ("core.alternateRefsCommand", "/bin/sh"),
        ("core.hooksPath", "/tmp/hooks"),
        ("core.attributesFile", "/tmp/attributes"),
        ("filter.other.clean", "/bin/sh"),
        ("filter.lfs.clean", "/bin/sh"),
        ("diff.tool.textconv", "/bin/sh"),
        ("merge.driver.driver", "/bin/sh"),
        ("merge.conflictStyle", "diff3"),
        ("submodule.recurse", "true"),
        ("hook.audit.command", "/bin/sh"),
        ("gpg.format", "ssh"),
        ("gpg.ssh.program", "/bin/sh"),
        ("gpg.x509.program", "/bin/sh"),
        ("gpg.program", "/usr/local/bin/gpg"),
    ],
)
def test_only_the_allowlisted_configuration_entries_may_appear(lane, key, value):
    command = lane.command("push")
    configure(lane, "common", key, value)
    result = lane.pre(lane.payload(command))
    assert result.refused
    if key.endswith(".insteadOf"):
        # The rewritten origin already fails the managed-project identity check.
        assert "disagrees with origin" in result.err
    else:
        assert "configuration refuses" in result.err


def test_the_credential_helpers_must_equal_the_profile_list(lane):
    write(lane.home / ".gitconfig", GLOBAL_CONFIG.replace("\thelper =\n", "", 1))
    assert lane.pre(lane.payload(lane.command("push"))).refused


def test_the_allowlisted_entries_are_accepted(lane):
    configure(lane, "common", "gpg.program", "/usr/bin/gpg")
    configure(lane, "common", "push.autoSetupRemote", "true")
    assert lane.pre(lane.payload(lane.command("push"))).approved


# --- Hooks, attributes and drivers --------------------------------------------------


@pytest.mark.parametrize(
    "defect", ["regular", "symlink", "symlinked-sample", "admin", "hooks-directory-symlink"]
)
@pytest.mark.parametrize("operation", OPERATIONS)
def test_no_hook_may_be_installed(lane, operation, defect):
    command = lane.command(operation)
    hooks = lane.canonical / ".git/hooks"
    hooks.mkdir(exist_ok=True)
    if defect == "regular":
        write(hooks / "pre-push", "#!/bin/sh\nexit 0\n")
    elif defect == "symlink":
        (hooks / "pre-push").symlink_to("/bin/true")
    elif defect == "symlinked-sample":
        (hooks / "extra.sample").symlink_to(lane.body)
    elif defect == "admin":
        write(lane.admin / "hooks/post-checkout", "#!/bin/sh\nexit 0\n")
    else:
        moved = lane.tmp_path / "hooks-real"
        hooks.rename(moved)
        hooks.symlink_to(moved, target_is_directory=True)
    result = lane.pre(lane.payload(command))
    assert result.refused and "hook" in result.err


@pytest.mark.parametrize(
    "defect",
    [
        "tracked-filter",
        "tracked-diff",
        "tracked-merge",
        "nested-tracked",
        "untracked",
        "ignored-untracked",
        "canonical-untracked",
        "info-common",
        "info-admin",
        "global",
        "xdg",
        "gitlink",
    ],
)
@pytest.mark.parametrize("operation", OPERATIONS)
def test_no_attribute_may_select_a_driver_and_no_gitlink_may_exist(lane, operation, defect):
    if defect == "tracked-filter":
        lane.commit("chore: attributes", {".gitattributes": "*.bin filter=lfs\n"})
    elif defect == "tracked-diff":
        lane.commit("chore: attributes", {".gitattributes": "*.txt diff=custom\n"})
    elif defect == "tracked-merge":
        lane.commit("chore: attributes", {".gitattributes": "*.txt merge=ours\n"})
    elif defect == "nested-tracked":
        lane.commit("chore: attributes", {"docs/.gitattributes": "*.md filter=lfs\n"})
    elif defect == "untracked":
        write(lane.worktree / ".gitattributes", "*.bin filter=lfs\n")
    elif defect == "ignored-untracked":
        write(lane.worktree / ".aegis/.gitattributes", "* diff=custom\n")
    elif defect == "canonical-untracked":
        write(lane.canonical / "docs/.gitattributes", "*.md merge=ours\n")
    elif defect == "info-common":
        write(lane.canonical / ".git/info/attributes", "")
    elif defect == "info-admin":
        write(lane.admin / "info/attributes", "")
    elif defect == "global":
        write(lane.home / ".config/git/attributes", "")
    elif defect == "xdg":
        write(Path(os.environ["XDG_CONFIG_HOME"]) / "git/attributes", "")
    else:
        git(lane.worktree, "update-index", "--add", "--cacheinfo", f"160000,{lane.head()},vendor/sub")
        lane.commit_index("chore: vendor a submodule")
    result = lane.pre(lane.payload(lane.command(operation)))
    assert result.refused, result.err


def test_an_attributes_file_without_a_driver_is_accepted(lane):
    lane.commit("chore: attributes", {".gitattributes": "*.sh text eol=lf\n"})
    write(lane.worktree / "docs/.gitattributes", "*.md text\n")
    assert lane.pre(lane.payload(lane.command("push"))).approved


# --- gh, PATH and branch names -------------------------------------------------------


@pytest.mark.parametrize("scope", ["http_unix_socket", "github.com"])
@pytest.mark.parametrize("operation", OPERATIONS)
def test_a_set_gh_unix_socket_refuses(lane, operation, scope):
    lane.transport.socket[scope] = b"/run/gh.sock\n"
    result = lane.pre(lane.payload(lane.command(operation)))
    assert result.refused and "http_unix_socket" in result.err


def test_an_earlier_git_on_the_delivery_path_refuses(lane):
    bindir = lane.tmp_path / "bin"
    write(bindir / "git", "#!/bin/sh\nexit 0\n")
    (bindir / "git").chmod(0o755)
    lane.set_profile(delivery_path=f"{bindir}:/usr/bin:/bin")
    result = lane.pre(lane.payload(lane.command("push")))
    assert result.refused and "first git" in result.err


@pytest.mark.parametrize("shadow", ["tag", "remote", "bare-ref", "pseudo-ref"])
@pytest.mark.parametrize("operation", OPERATIONS)
def test_the_branch_resolves_only_as_a_branch(lane, operation, shadow):
    if shadow == "tag":
        git(lane.worktree, "tag", BRANCH)
    elif shadow == "remote":
        git(lane.worktree, "update-ref", f"refs/remotes/{BRANCH}", "HEAD")
    elif shadow == "bare-ref":
        git(lane.worktree, "update-ref", f"refs/{BRANCH}", "HEAD")
    else:
        write(lane.canonical / ".git" / BRANCH, lane.head() + "\n")
    result = lane.pre(lane.payload(lane.command(operation)))
    assert result.refused and "shares the branch name" in result.err


# --- Pull requests ------------------------------------------------------------------


def test_pr_create_needs_the_pushed_branch_to_be_head(lane):
    lane.publish()
    lane.commit("feat: later", {"src/later.txt": "later\n"})
    assert lane.pre(lane.payload(lane.create())).refused
    git(lane.bare, "update-ref", "-d", f"refs/heads/{BRANCH}")
    assert lane.pre(lane.payload(lane.create())).refused


@pytest.mark.parametrize(
    "defect", ["untracked", "ignored", "symlinked-file", "symlinked-directory", "hardlink",
               "oversized", "outside", "directory"]
)
def test_the_body_file_is_a_tracked_single_regular_file_inside_the_worktree(lane, defect):
    body = lane.body
    if defect == "untracked":
        body = lane.worktree / "docs/untracked.md"
        write(body, "not committed\n")
    elif defect == "ignored":
        body = lane.worktree / ".aegis/body.md"
        write(body, "ignored\n")
    elif defect == "symlinked-file":
        (lane.worktree / "docs/link.md").symlink_to("pr-body.md")
        git(lane.worktree, "add", "docs/link.md")
        lane.commit_index("docs: link the body")
        body = lane.worktree / "docs/link.md"
    elif defect == "symlinked-directory":
        (lane.worktree / "linked").symlink_to("docs", target_is_directory=True)
        git(lane.worktree, "add", "linked")
        lane.commit_index("docs: link the docs")
        body = lane.worktree / "linked/pr-body.md"
    elif defect == "hardlink":
        os.link(lane.body, lane.tmp_path / "second-name.md")
    elif defect == "oversized":
        lane.commit("docs: a long body", {"docs/pr-body.md": "x" * (64 * 1024 + 1)})
    elif defect == "outside":
        body = lane.canonical / "README.md"
    else:
        body = lane.worktree / "docs"
    lane.publish()
    assert lane.pre(lane.payload(lane.create(body=body))).refused


def test_a_body_whose_bytes_differ_from_heads_blob_refuses(lane):
    write(lane.body, "uncommitted text\n")
    checkout = delivery_worktree.verify_checkout(lane.worktree, lane.canonical, lane.worktree.parent)
    reader = delivery_checks.Reader(str(lane.home), DELIVERY_PATH, delivery_checks.clock() + 60)
    assert (
        delivery_checks.body_violation(reader, checkout, str(lane.body))
        == "the body file bytes differ from HEAD's blob"
    )
    lane.publish()
    assert lane.pre(lane.payload(lane.create())).refused


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "MERGED"},
        {"state": "CLOSED"},
        {"isCrossRepository": True},
        {"isCrossRepository": None},
        {"baseRefName": "develop"},
        {"headRefName": "codex/ga-other-branch"},
        {"headRefOid": "0" * 40},
    ],
)
def test_the_merge_needs_an_open_same_repository_pr_on_the_exact_head(lane, changes):
    lane.publish()
    lane.pull_request(**changes)
    assert lane.pre(lane.payload(lane.merge())).refused


ROLLUPS = {
    "failing-check": [{"__typename": "CheckRun", "name": "ci / test", "conclusion": "FAILURE"}],
    "pending-check": [
        {"__typename": "CheckRun", "name": "ci / test", "status": "IN_PROGRESS", "conclusion": ""}
    ],
    "skipped-check": [{"__typename": "CheckRun", "name": "ci / test", "conclusion": "SKIPPED"}],
    "failing-status": [
        {"__typename": "CheckRun", "name": "ci / test", "conclusion": "SUCCESS"},
        {"__typename": "StatusContext", "context": "lint", "state": "FAILURE"},
    ],
    "missing-required": [{"__typename": "CheckRun", "name": "lint", "conclusion": "SUCCESS"}],
    "unknown-entry": [
        {"__typename": "CheckRun", "name": "ci / test", "conclusion": "SUCCESS"},
        {"__typename": "Other", "name": "x"},
    ],
    "hundred-entries": [
        {"__typename": "CheckRun", "name": f"check {index}", "conclusion": "SUCCESS"}
        for index in range(99)
    ]
    + [{"__typename": "CheckRun", "name": "ci / test", "conclusion": "SUCCESS"}],
    "not-a-list": None,
}


@pytest.mark.parametrize("rollup", sorted(ROLLUPS))
def test_the_merge_needs_a_complete_green_rollup_with_the_required_checks(lane, rollup):
    lane.publish()
    lane.pull_request(statusCheckRollup=ROLLUPS[rollup])
    assert lane.pre(lane.payload(lane.merge())).refused


def test_ninety_nine_green_entries_are_accepted(lane):
    lane.publish()
    lane.pull_request(statusCheckRollup=ROLLUPS["hundred-entries"][1:])
    assert lane.pre(lane.payload(lane.merge())).approved


def test_a_merge_of_a_commit_that_is_not_the_worktree_head_refuses(lane):
    old = lane.head()
    lane.commit("feat: later", {"src/later.txt": "later\n"})
    lane.publish()
    lane.pull_request(headRefOid=old)
    assert lane.pre(lane.payload(lane.merge(sha=old))).refused


# --- Modes and workflow state -------------------------------------------------------


@pytest.mark.parametrize("mode", ["plan", "unknown", None])
@pytest.mark.parametrize("operation", OPERATIONS)
def test_plan_and_unknown_modes_refuse(lane, operation, mode):
    result = lane.pre(lane.payload(lane.command(operation), permission_mode=mode))
    assert result.refused
    if mode == "plan":
        assert read_gate_decisions(lane.canonical)[-1]["reason"] == "plan_mode_mutation"


@pytest.mark.parametrize("scope", ["seat", "worktree"])
@pytest.mark.parametrize("state", ["observation", "pending"])
@pytest.mark.parametrize("operation", OPERATIONS)
def test_observation_and_pending_state_refuse_at_seat_and_worktree(lane, operation, state, scope):
    root = lane.canonical if scope == "seat" else lane.worktree
    if state == "observation":
        write(root / ".aegis/state/current-work.json", current_work(root, mode="observation"))
    else:
        write(
            root / ".aegis/state/pending-tracking.json",
            json.dumps({"events": [{"id": "0123456789ab", "mode": "strict", "kind": "mutation"}]}),
        )
    assert lane.pre(lane.payload(lane.command(operation))).refused


def test_background_runs_refuse(lane):
    call = lane.payload(lane.command("push"))
    call["tool_input"]["run_in_background"] = True
    result = lane.pre(call)
    assert result.refused and "run_in_background" in result.err


@pytest.mark.parametrize("missing", ["tool_use_id", "session_id"])
def test_a_payload_without_its_call_identity_refuses(lane, missing):
    call = lane.payload(lane.command("push"))
    del call[missing]
    assert lane.pre(call).refused
    assert not lane.bindings()


def test_a_call_from_another_directory_refuses(lane):
    call = lane.payload(lane.command("push"), cwd=str(lane.worktree))
    assert lane.pre(call).refused


def test_an_advisory_target_refuses_delivery(lane):
    write(lane.worktree / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    result = lane.pre(lane.payload(lane.command("push")))
    assert result.refused and "advisory target" in result.err
    assert not lane.bindings()


def test_a_gate_failure_never_degrades_a_delivery_call_into_an_allow(lane, monkeypatch):
    from aegis_foundation.gate.hooks import pretool

    write(lane.canonical / ".aegis/state/enforcement.json", '{"mode":"advisory"}')

    def explode(*_args, **_kwargs):
        raise RuntimeError("synthetic infrastructure failure")

    monkeypatch.setattr(pretool, "evaluate_native_delegation", explode)
    result = lane.pre(lane.payload(lane.command("push")))
    assert result.refused and "coordination cannot use degraded approval" in result.err
    assert not (lane.canonical / AEGIS_DEGRADED_EVENTS_REL).exists()


# --- Tracking through the binding ---------------------------------------------------


def move_remote_main(lane: Lane) -> None:
    """GitHub merged the PR: the remote main is a new merge commit, not an ancestor of HEAD."""

    main = run(["git", "rev-parse", "main"], lane.canonical).stdout.strip()
    tree = run(["git", "rev-parse", "HEAD^{tree}"], lane.worktree).stdout.strip()
    merge = run(
        ["git", "commit-tree", tree, "-p", main, "-p", lane.head(), "-m", "Merge pull request #7"],
        lane.canonical,
    ).stdout.strip()
    git(lane.canonical, "push", "-q", "--force", str(lane.bare), f"{merge}:refs/heads/main")


def discharge_payload(lane: Lane, event_id: str) -> str:
    command = (
        f"python3 {lane.canonical / WORKFLOW_REL} discharge --root {lane.worktree} "
        f"--pending-id {event_id} --note recorded"
    )
    return json.dumps(lane.payload(command))


@pytest.mark.parametrize("operation", OPERATIONS)
def test_a_successful_call_leaves_one_delivery_event_that_discharge_resolves(lane, operation):
    command = lane.command(operation)
    call = lane.payload(command)
    assert lane.pre(call).approved
    if operation == "pr-merge":
        lane.transport.pr["state"] = "MERGED"
        move_remote_main(lane)
    result = lane.post(call)
    assert result.code == 0, result.err
    [event] = lane.events()
    assert event["kind"] == "delivery" and event["evidence"] == f"cmd`{command}`"
    assert not lane.events(lane.canonical) and not lane.bindings()
    # Pending events come one at a time: the next delivery step refuses until discharge.
    assert lane.pre(lane.payload(lane.push())).refused
    request = discharge_payload(lane, event["id"])
    allowed = run_gate(PRETOOLUSE, lane.canonical, request)
    assert allowed.returncode == 0, allowed.stderr
    assert '"permissionDecision": "allow"' in allowed.stdout
    # The executor records the event into the journal and removes exactly that event.
    (lane.worktree / ".aegis/state/pending-tracking.json").unlink()
    assert run_gate(POSTTOOLUSE, lane.canonical, request).returncode == 0
    assert not lane.events() and not lane.events(lane.canonical)


def test_a_runtime_changing_branch_is_pushed_but_not_discharged_from_the_seat(lane):
    """Known limit: coordinate's reviewed-runtime check still refuses stationary discharge."""

    lane.commit("feat: a runtime module", {"scripts/delivery_extra.py": "# new runtime\n"})
    call = lane.payload(lane.command("push"))
    assert lane.pre(call).approved
    assert lane.post(call).code == 0
    [event] = lane.events()
    refused = run_gate(PRETOOLUSE, lane.canonical, discharge_payload(lane, event["id"]))
    assert refused.returncode == 2
    assert "unreviewed runtime file" in refused.stderr
    assert lane.events() == [event]


@pytest.mark.parametrize("operation", OPERATIONS)
def test_a_failed_call_then_a_retry_leaves_exactly_one_delivery_event(lane, operation):
    command = lane.command(operation)
    first = lane.payload(command)
    assert lane.pre(first).approved
    assert lane.failed(first).code == 0
    assert not lane.bindings() and not lane.events()
    retry = lane.payload(command)
    assert lane.pre(retry).approved
    assert lane.post(retry).code == 0
    assert [event["kind"] for event in lane.events()] == ["delivery"]


@pytest.mark.parametrize("operation", OPERATIONS)
def test_posttool_for_another_call_cannot_consume_a_binding(lane, operation):
    call = lane.payload(lane.command(operation))
    assert lane.pre(call).approved
    other = {**call, "tool_use_id": "toolu_other"}
    result = lane.post(other)
    assert result.code == 2 and "stop and reconcile" in result.err
    assert read_gate_decisions(lane.canonical)[-1]["reason"] == "coordination_target_invalid"
    assert not lane.events() and len(lane.bindings()) == 1
    assert lane.post(call).code == 0
    assert len(lane.events()) == 1 and not lane.bindings()
    # A consumed binding is never consumed again.
    assert lane.post(call).code == 2
    assert len(lane.events()) == 1


def test_posttool_without_a_tool_use_id_refuses(lane):
    call = lane.payload(lane.command("push"))
    assert lane.pre(call).approved
    stripped = {key: value for key, value in call.items() if key != "tool_use_id"}
    assert lane.post(stripped).code == 2
    assert not lane.events()


@pytest.mark.parametrize("operation", OPERATIONS)
def test_an_advisory_seats_manually_approved_delivery_is_tracked(lane, operation):
    write(lane.canonical / ".aegis/state/enforcement.json", '{"mode":"advisory"}')
    call = lane.payload(lane.command(operation))
    result = lane.pre(call)
    assert result.code == 0 and '"permissionDecision"' not in result.out
    record = read_gate_decisions(lane.worktree)[-1]
    assert record["verdict"] == "allow"
    assert record["reason"] == "advisory_delivery_no_native_approval"
    assert len(lane.bindings()) == 1
    assert lane.post(call).code == 0  # the operator approved it by hand and it ran
    assert [event["kind"] for event in lane.events()] == ["delivery"]


def test_a_second_call_for_the_same_worktree_refuses_while_a_binding_is_live(lane):
    assert lane.pre(lane.payload(lane.command("push"))).approved
    result = lane.pre(lane.payload(lane.command("push")))
    assert result.refused and "in flight" in result.err
    assert len(lane.bindings()) == 1


def test_bindings_expire_after_thirty_minutes(lane, monkeypatch):
    first = lane.payload(lane.command("push"))
    assert lane.pre(first).approved
    later = time.time() + delivery_binding.EXPIRY_SECONDS + 1
    monkeypatch.setattr(delivery_binding, "wall_clock", lambda: later)
    # A call that outlives its binding leaves no event.
    assert lane.post(first).code == 2
    assert not lane.events()
    # An expired binding no longer holds the worktree.
    second = lane.payload(lane.command("push"))
    assert lane.pre(second).approved
    stale = lane.payload(lane.command("push"))
    monkeypatch.setattr(delivery_binding, "wall_clock", lambda: later + 2 * delivery_binding.EXPIRY_SECONDS)
    assert lane.pre(stale).approved
    assert len(lane.bindings()) == 1


def _synthetic_binding(directory: Path, index: int, worktree: str) -> None:
    record = {
        "schema": delivery_binding.BINDING_SCHEMA,
        "operation": "push",
        "worktree": worktree,
        "created": time.time(),
    }
    write(directory / f"{index:064x}.json", json.dumps(record))


def test_at_most_sixteen_bindings_exist(lane):
    directory = lane.canonical / ".aegis/state/delivery-bindings"
    for index in range(16):
        _synthetic_binding(directory, index, f"/elsewhere/worktree-{index}")
    result = lane.pre(lane.payload(lane.command("push")))
    assert result.refused and "too many" in result.err
    (directory / f"{0:064x}.json").unlink()
    assert lane.pre(lane.payload(lane.command("push"))).approved


def test_any_pretooluse_prunes_expired_bindings(lane):
    directory = lane.canonical / ".aegis/state/delivery-bindings"
    _synthetic_binding(directory, 1, "/elsewhere/worktree-1")
    _synthetic_binding(directory, 2, "/elsewhere/worktree-2")
    stale = directory / f"{1:064x}.json"
    record = json.loads(stale.read_text())
    record["created"] = time.time() - delivery_binding.EXPIRY_SECONDS - 5
    stale.write_text(json.dumps(record))
    # An unrelated call, refused by the seat's BLOCKED readiness, still prunes.
    assert lane.pre(lane.payload("touch marker")).code == 2
    assert [path.name for path in lane.bindings()] == [f"{2:064x}.json"]


def test_a_symlinked_binding_directory_or_file_refuses(lane):
    real = lane.tmp_path / "elsewhere-bindings"
    real.mkdir()
    state = lane.canonical / ".aegis/state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "delivery-bindings").symlink_to(real, target_is_directory=True)
    assert lane.pre(lane.payload(lane.command("push"))).refused
    assert not list(real.iterdir())
    (state / "delivery-bindings").unlink()
    (state / "delivery-bindings").mkdir()
    (state / "delivery-bindings" / ("f" * 64 + ".json")).symlink_to(real / "target.json")
    assert lane.pre(lane.payload(lane.command("push"))).refused


def test_an_invalid_binding_record_holds_every_worktree_until_it_ages_out(lane, monkeypatch):
    directory = lane.canonical / ".aegis/state/delivery-bindings"
    write(directory / ("e" * 64 + ".json"), "not json")
    assert lane.pre(lane.payload(lane.command("push"))).refused
    later = time.time() + delivery_binding.EXPIRY_SECONDS + 1
    monkeypatch.setattr(delivery_binding, "wall_clock", lambda: later)
    assert lane.pre(lane.payload(lane.command("push"))).approved


@pytest.mark.parametrize("field_name", ["worktree", "operation"])
def test_a_rewritten_binding_cannot_retarget_the_event(lane, field_name):
    call = lane.payload(lane.command("push"))
    assert lane.pre(call).approved
    [binding] = lane.bindings()
    record = json.loads(binding.read_text())
    record[field_name] = (
        str(lane.worktree.parent / "ga-other-slug") if field_name == "worktree" else "pr-merge"
    )
    binding.write_text(json.dumps(record))
    assert lane.post(call).code == 2
    assert not lane.events()


def test_the_failure_handler_is_a_synchronous_entrypoint_subcommand(lane, monkeypatch):
    from aegis_foundation.gate.hooks import entrypoint

    call = lane.payload(lane.command("push"))
    assert lane.pre(call).approved
    monkeypatch.setattr(sys, "argv", ["gate_lib.py", "deliveryfailure"])
    event = {**call, "hook_event_name": "PostToolUseFailure", "error": "exit status 1"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    assert entrypoint.main() == 0
    assert not lane.bindings() and not lane.events()


def test_the_launcher_routes_the_failure_subcommand(tmp_path):
    event = {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "tool_input": {"command": "ls"}}
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / ".claude/scripts/gate_lib.py"), "deliveryfailure"],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)},
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_an_approval_that_is_not_emitted_removes_its_binding(lane, monkeypatch):
    from aegis_foundation.gate.hooks import decisions

    real = decisions.append_gate_decision

    def failing(root, **kwargs):
        if kwargs.get("reason") == "native_permission:delivery":
            raise OSError("audit unavailable")
        return real(root, **kwargs)

    monkeypatch.setattr(decisions, "append_gate_decision", failing)
    result = lane.pre(lane.payload(lane.command("push")))
    assert result.refused and "could not establish an audited approval" in result.err
    assert not lane.bindings()


# --- The deadline -------------------------------------------------------------------


def test_each_read_timeout_is_the_smaller_of_thirty_seconds_and_the_time_left(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(delivery_checks, "clock", lambda: now[0])
    reader = delivery_checks.Reader("/home/x", "/usr/bin:/bin", deadline=1045.0)
    assert reader.timeout() == 30
    now[0] = 1040.0
    assert reader.timeout() == 5
    now[0] = 1045.0
    with pytest.raises(delivery_checks.DeliveryRefusal, match="deadline"):
        reader.timeout()


def test_an_evaluation_whose_reads_pass_the_deadline_refuses(lane, monkeypatch):
    real = delivery_checks.clock
    ticks = [0]

    def slow() -> float:
        ticks[0] += 1
        return real() + 3.0 * ticks[0]

    monkeypatch.setattr(delivery_checks, "clock", slow)
    command = lane.command("pr-merge")
    lane.transport.calls.clear()
    result = lane.pre(lane.payload(command))
    assert result.refused and "deadline" in result.err
    timeouts = [
        kwargs["timeout"] for argv, kwargs in lane.transport.calls if argv[1] != "check-ref-format"
    ]
    assert timeouts and all(0 < timeout <= 30 for timeout in timeouts)
    assert min(timeouts) < 30  # reads near the deadline get only the time left
    assert not lane.bindings()


def test_the_deadline_is_checked_again_just_before_the_approval_return(lane, monkeypatch):
    monkeypatch.setattr(delivery, "clock", lambda: time.monotonic() + 61)
    result = lane.pre(lane.payload(lane.command("push")))
    assert result.refused and "deadline" in result.err
    assert not lane.bindings()


# --- Profile ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"required_checks": []},
        {"required_checks": ["ci / test", "ci / test"]},
        {"repository": "fixture-project"},
        {"repository": "example/fixture/project"},
        {"default_branch": "-main"},
        {"default_branch": "main..x"},
        {"remote_url": "ext::sh -c touch"},
        {"remote_url": ""},
        {"signing_key": "FD55"},
        {"delivery_path": "/usr/bin::/bin"},
        {"delivery_path": "usr/bin:/bin"},
        {"delivery_home": "/home/x/"},
        {"credential_helpers": [{"key": "helper", "value": ""}]},
        {"credential_helpers": {"key": "credential.helper"}},
        {"unknown_field": True},
        {"signing_key": None},
    ],
)
def test_an_invalid_or_incomplete_delivery_profile_refuses(lane, changes):
    value = lane.profile()
    value.update(changes)
    if changes.get("signing_key", "") is None:
        del value["signing_key"]
    lane.write_profile(value)
    result = lane.pre(lane.payload(lane.command("push")))
    assert result.refused


def test_delivery_fields_without_the_opt_in_grant_nothing(lane):
    value = lane.profile()
    value["commands"].remove("delivery")
    lane.write_profile(value)
    assert not lane.pre(lane.payload(lane.command("push"))).approved


def test_the_live_profile_still_loads_its_registered_projects():
    from aegis_foundation.gate.hooks.native_permissions import COMMANDS

    assert "delivery" in COMMANDS
    value = json.loads((REPO_ROOT / PROFILE).read_text())
    assert set(value["commands"]) <= COMMANDS


# --- Settings -----------------------------------------------------------------------


def test_live_settings_bound_the_gate_and_register_the_binding_handler():
    settings = json.loads((REPO_ROOT / ".claude/settings.json").read_text())
    [pretool] = [
        hook
        for group in settings["hooks"]["PreToolUse"]
        for hook in group["hooks"]
        if hook["command"].endswith("pretooluse-gate.sh")
    ]
    assert pretool["timeout"] == 120
    handlers = [
        hook
        for group in settings["hooks"]["PostToolUseFailure"]
        for hook in group["hooks"]
        if hook["command"].endswith("gate_lib.py deliveryfailure")
    ]
    assert handlers == [
        {
            "type": "command",
            "command": "python3 $CLAUDE_PROJECT_DIR/.claude/scripts/gate_lib.py deliveryfailure",
        }
    ]


# --- Shared classifiers stay unchanged ----------------------------------------------


def test_the_shared_prefix_classifiers_are_unchanged():
    source = inspect.getsource(payloads.strip_shell_prefixes).encode()
    assert (
        hashlib.sha256(source).hexdigest()
        == "b163b8218e7835f473d4fe78a5672b9e92d08cf89342c5e0737bf02e4f89123d"
    )
    assert contracts.ORCHESTRATOR_ENVIRONMENT == {
        "PATH": "/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin",
        "GC_HOME": "/home/loucmane/gascity/home",
    }
    assert contracts.ORCHESTRATOR_ENV_UNSET == frozenset({"BEADS_DIR", "BEADS_DB"})
    assert contracts.DELIVERY_COMMAND_RE.pattern == (
        r"(^|[;&|]\s*)(git\s+push\b|gh\s+pr\s+(create|merge|ready)\b)"
    )


@pytest.mark.parametrize("values", ["delivery", "operator", "none"])
def test_other_classes_still_treat_an_env_i_prefix_as_untrusted(lane, values):
    if values == "delivery":
        extra = [f"HOME={lane.home}", f"PATH={DELIVERY_PATH}"]
    elif values == "operator":
        extra = ["GC_HOME=/home/loucmane/gascity/home", "PATH=/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin"]
    else:
        extra = []
    prefix = ["/usr/bin/env", "-i", *extra]
    commands = [
        ["python3", str(lane.canonical / CONTEXT_REL), "--root", str(lane.canonical), "--check"],
        [
            "/home/loucmane/gascity/bin/gc",
            "--city",
            "/home/loucmane/gascity/city",
            "--rig",
            "gascity",
            "bd",
            "show",
            "ga-one",
            "--json",
        ],
        ["/usr/bin/git", "ls-remote", "origin", "refs/heads/main"],
        ["/usr/bin/git", "fetch", "origin"],
        ["/usr/bin/gh", "pr", "view", "7"],
        ["python3", str(lane.canonical / WORKFLOW_REL), "begin", "--root", str(lane.canonical), "--bead", "ga-one"],
        ["python3", str(lane.canonical / WORKFLOW_REL), "checkpoint", "--root", str(lane.worktree)],
    ]
    for words in commands:
        tokens = [*prefix, *words]
        command = shlex.join(tokens)
        assert payloads.strip_shell_prefixes(tokens)[0] == UNTRUSTED
        assert not shell_policy.bash_is_read_only(command)
        assert not shell_policy.bash_is_delivery_command(command)
        result = lane.pre(lane.payload(command))
        assert result.code == 2 and '"permissionDecision": "allow"' not in result.out, command


def test_the_shared_classifier_still_records_an_env_i_push_as_a_mutation(lane):
    from aegis_foundation.gate.hooks.evidence import pending_event_kind

    payload = Payload("Bash", {"command": lane.push()})
    assert pending_event_kind(payload) == "mutation"


def test_the_ledger_classifies_delivery_through_the_delivery_parser(lane):
    data = {"hook_event_name": "PostToolUse"}
    command = lane.push()
    assert (
        tracking._classify_record_event(data, Payload("Bash", {"command": command}), [], "pass", lane.canonical)
        == "delivery"
    )
    other = replace_once(command, f"HOME={lane.home}", "HOME=/tmp")
    assert (
        tracking._classify_record_event(data, Payload("Bash", {"command": other}), [], "pass", lane.canonical)
        == "mutation"
    )
