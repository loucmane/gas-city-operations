"""The Template candidate lane is closed, source-selected, and receipt-ready."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tomllib

import pytest

from lib import gct_claude_signing_worker as signing_worker
from lib import gct_claude_template_candidate_worker as template_worker
from test_operations_candidate_worker import (
    _installed_paths,
    _provision,
    _provisioning_prototype,
    _record,
    _render,
)


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "bin/gct-claude-template-candidate-worker"
POLICY = ROOT / "templates/claude/template-candidate-control-policy.json"
OPERATIONS_POLICY = ROOT / "templates/claude/candidate-control-policy.json"
CORE_POLICY = ROOT / "templates/claude/core-signing-control-policy.json"
PROVIDER = ROOT / "templates/claude/template-candidate-provider.toml"
PROFILE = ROOT / "managed/profiles/gas-city-template-candidate-claude.json"
RUNNER = ROOT / "bin/gct-managed-worker-canary"
UNKNOWN_POLICY = ROOT / "tests/fixtures/unknown-candidate-control-policy.json"
RENDERER = ROOT / "bin/gct-managed-rig-permissions"
CORE_SIGNING_PROFILE = ROOT / "managed/profiles/gascity-claude-signing.json"
OPERATIONS_PROFILE = ROOT / "managed/profiles/gascity-operations-candidate-claude.json"
GOLDEN = ROOT / "tests/fixtures/template-candidate-render-golden"
TEMPLATE_ROOT = "/home/loucmane/gas-city-template-candidate-worktrees"
WORKTREES_RULE = f"Edit(/{TEMPLATE_ROOT}/*/**)"
GIT_LINK_DENY = f"Edit(/{TEMPLATE_ROOT}/*/.git)"
FILE_TOOLS = ("Edit", "Write", "NotebookEdit", "MultiEdit")
CONTROL_COMMANDS = [
    "/home/loucmane/gascity/bin/gc hook --claim --json",
    "/home/loucmane/gascity/bin/gc runtime drain-ack",
    "/home/loucmane/gascity/bin/bd close *",
    "/home/loucmane/gascity/bin/bd show *",
    "/home/loucmane/gascity/bin/bd update *",
]


def _policy() -> dict[str, object]:
    return json.loads(POLICY.read_text(encoding="utf-8"))


def _config(tmp_path: Path) -> signing_worker.LaunchConfig:
    claude = tmp_path / "claude"
    claude.write_bytes(b"synthetic claude\n")
    claude.chmod(0o755)
    shared = tmp_path / "city/.gc/settings.json"
    shared.parent.mkdir(parents=True)
    shared.write_text("{}", encoding="utf-8")
    policy = tmp_path / "source/policy.json"
    policy.parent.mkdir(parents=True)
    policy.write_bytes(POLICY.read_bytes())
    policy.chmod(0o600)
    worktrees = tmp_path / "worktrees"
    worktrees.mkdir()
    dependencies = []
    for name in ("entrypoint", "candidate", "boundary", "subscription", "provider"):
        dependency = tmp_path / "source" / name
        dependency.write_text(name + "\n", encoding="utf-8")
        dependencies.append(dependency)
    return signing_worker.LaunchConfig(
        claude=claude,
        shared_settings=shared,
        control_policy=policy,
        add_dirs=(worktrees,),
        source_dependencies=tuple(dependencies),
    )


def _arguments(config: signing_worker.LaunchConfig, *, resume: bool = False) -> list[str]:
    arguments = ["--resume", "session-fixture-1"] if resume else []
    arguments.extend(
        [
            "--model",
            "claude-opus-5-5",
            "--effort",
            "max",
            "--permission-mode",
            "dontAsk",
            "--settings",
            str(config.control_policy),
            "--add-dir",
            str(config.add_dirs[0]),
        ]
    )
    if not resume:
        arguments.extend(["--settings", str(config.shared_settings)])
    return arguments


def _linked(worktree: Path, common: Path, name: str = "gct-fixture") -> Path:
    worktree.mkdir(parents=True, exist_ok=True)
    admin = common / "worktrees" / name
    admin.mkdir(parents=True, exist_ok=True)
    (worktree / ".git").write_text(f"gitdir: {admin}\n", encoding="utf-8")
    (admin / "gitdir").write_text(f"{worktree}/.git\n", encoding="utf-8")
    (admin / "commondir").write_text("../..\n", encoding="utf-8")
    return worktree


def test_default_config_is_template_scoped_and_reuses_the_core_boundary() -> None:
    config = template_worker.default_config()
    assert config.control_policy == POLICY
    assert config.add_dirs == (ROOT.parent / "gas-city-template-candidate-worktrees",)
    assert template_worker._TEMPLATE_COMMON == ROOT.parent / "gas-city-template/.git"
    assert template_worker._BOUNDARY_SOURCE == ROOT / "lib/gct_claude_signing_worker.py"
    assert template_worker._EXECUTED_BOUNDARY_SOURCE == (
        ROOT / "lib/gct_claude_signing_worker.py"
    ).read_bytes()
    assert signing_worker.default_config().control_policy == CORE_POLICY


@pytest.mark.parametrize("resume", [False, True], ids=["initial", "resume"])
def test_launch_removes_shared_settings_and_loads_only_template_policy(
    tmp_path: Path, resume: bool
) -> None:
    config = _config(tmp_path)
    calls: list[list[str]] = []

    def authenticate(*_args: object, **kwargs: object) -> dict[str, object]:
        assert kwargs["setting_sources"] == ""
        return {
            "loggedIn": True,
            "authMethod": "claude.ai",
            "apiProvider": "firstParty",
            "apiKeySource": None,
            "subscriptionType": "max",
        }

    class Executed(Exception):
        pass

    def execve(_path: str, argv: list[str], _environment: dict[str, str]) -> None:
        calls.append(argv)
        raise Executed

    with pytest.raises(Executed):
        template_worker.boundary.launch(
            _arguments(config, resume=resume),
            parent_environment={"PATH": "/usr/bin:/bin"},
            cwd=Path.cwd(),
            config=config,
            authenticate=authenticate,
            execve=execve,
        )
    (argv,) = calls
    assert str(config.shared_settings) not in argv
    assert argv[argv.index("--settings") - 2 : argv.index("--settings") + 2] == [
        "--setting-sources",
        "",
        "--settings",
        str(config.control_policy),
    ]
    assert [argv[i + 1] for i, value in enumerate(argv) if value == "--add-dir"] == [
        str(config.add_dirs[0])
    ]


@pytest.mark.parametrize(
    "extra,reason",
    [
        (["--settings", "/tmp/other.json"], "settings"),
        (["--add-dir", "/tmp/other"], "managed directory grant"),
        (["--dangerously-skip-permissions"], "caller-owned flag"),
        (["--resume", "second-session"], "resume"),
        (["--permission-mode", "auto"], "permission selection"),
    ],
)
def test_closed_argument_vocabulary_refuses_foreign_authority(
    tmp_path: Path, extra: list[str], reason: str
) -> None:
    config = _config(tmp_path)
    with pytest.raises(template_worker.CandidateWorkerError, match=reason):
        template_worker.boundary._validated_arguments(
            [*_arguments(config), *extra], config
        )


def test_launch_requires_a_physical_direct_linked_template_worktree(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    common = tmp_path / "gas-city-template/.git"
    worktree = _linked(config.add_dirs[0] / "gct-fixture", common)
    assert template_worker.require_candidate_worktree(worktree, config, common) == worktree

    deeper = worktree / "nested"
    deeper.mkdir()
    sibling = config.add_dirs[0].parent / "other/gct-fixture"
    sibling.mkdir(parents=True)
    symlink = config.add_dirs[0] / "gct-link"
    symlink.symlink_to(worktree)
    for refused in (config.add_dirs[0], deeper, sibling, symlink):
        with pytest.raises(template_worker.CandidateWorkerError, match="must start"):
            template_worker.require_candidate_worktree(refused, config, common)


@pytest.mark.parametrize(
    "damage",
    ["bad-gitfile", "wrong-gitdir", "wrong-commondir", "missing-admin", "directory-git"],
)
def test_template_worktree_linkage_refuses_wrong_repository_state(
    tmp_path: Path, damage: str
) -> None:
    config = _config(tmp_path)
    common = tmp_path / "gas-city-template/.git"
    worktree = _linked(config.add_dirs[0] / "gct-fixture", common)
    admin = common / "worktrees/gct-fixture"
    if damage == "bad-gitfile":
        (worktree / ".git").write_text("gitdir: /tmp/foreign\n", encoding="utf-8")
    elif damage == "wrong-gitdir":
        (admin / "gitdir").write_text("/tmp/elsewhere/.git\n", encoding="utf-8")
    elif damage == "wrong-commondir":
        (admin / "commondir").write_text("../../../other\n", encoding="utf-8")
    elif damage == "missing-admin":
        (worktree / ".git").write_text(
            f"gitdir: {common}/worktrees/missing\n", encoding="utf-8"
        )
    else:
        (worktree / ".git").unlink()
        (worktree / ".git").mkdir()
    with pytest.raises(template_worker.CandidateWorkerError, match="linked Template"):
        template_worker.require_candidate_worktree(worktree, config, common)


def test_entrypoint_provider_and_dependency_version_bind_both_launches(
    tmp_path: Path,
) -> None:
    assert os.access(ENTRYPOINT, os.X_OK)
    assert "exec /usr/bin/python3.12 -I -S -B" in ENTRYPOINT.read_text(encoding="utf-8")
    provider = tomllib.loads(PROVIDER.read_text(encoding="utf-8"))["providers"][
        "claude-template-candidate"
    ]
    assert provider["command"].endswith("/bin/gct-claude-template-candidate-worker")
    assert provider["resume_command"].endswith("--resume {{.SessionKey}}")
    assert provider["path_check"] == "/home/loucmane/gascity/bin/claude"

    entrypoint, _policy_path = _installed_template_wrapper(tmp_path)
    result = subprocess.run(
        [str(entrypoint), "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == 0, result.stderr
    baseline = result.stdout.strip()
    assert baseline.startswith("gct-claude-template-candidate-worker 1 ")
    source_root = entrypoint.parents[1]
    for relative in (
        "bin/gct-claude-template-candidate-worker",
        "lib/gct_claude_template_candidate_worker.py",
        "lib/gct_claude_signing_worker.py",
        "lib/gct_claude_subscription.py",
        "templates/claude/template-candidate-control-policy.json",
        "templates/claude/template-candidate-provider.toml",
    ):
        dependency = source_root / relative
        original = dependency.read_bytes()
        dependency.write_bytes(original + b"\n")
        try:
            changed = subprocess.run(
                [str(entrypoint), "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
                env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            )
            assert changed.returncode == 0, changed.stderr
            assert changed.stdout.strip() != baseline, relative
        finally:
            dependency.write_bytes(original)


def test_template_policy_is_exact_closed_candidate_authority() -> None:
    policy = _policy()
    assert policy["_gc"] == {
        "schema": "gc.candidate-control-policy.v1",
        "profile_kind": "candidate",
    }
    assert set(policy["_gc"]) == {"schema", "profile_kind"}
    allow = policy["permissions"]["allow"]
    assert allow == [
        "Read",
        "Glob",
        "Grep",
        WORKTREES_RULE,
        *[f"Bash({command})" for command in CONTROL_COMMANDS],
    ]
    assert not [rule for rule in allow if rule in FILE_TOOLS]
    assert [rule for rule in allow if rule.startswith(tuple(f"{x}(" for x in FILE_TOOLS))] == [
        WORKTREES_RULE
    ]
    deny = set(policy["permissions"]["deny"])
    assert {
        GIT_LINK_DENY,
        "Read(//home/loucmane/vaults/**)",
        "Read(//home/loucmane/.ssh/**)",
        "Read(//home/loucmane/.gnupg/**)",
        "Read(//home/loucmane/.config/gh/**)",
        "Read(//home/loucmane/.claude/**)",
        "Read(//home/loucmane/.claude.json)",
        "Read(//home/loucmane/gascity/city/.gc/settings.json)",
        "Read(//home/loucmane/.git-credentials)",
        "Read(//home/loucmane/.netrc)",
        "Read(//home/loucmane/.config/git/**)",
        "Bash(git commit *)",
        "Bash(git push *)",
        "Bash(git merge *)",
        "Bash(git config *)",
        "Bash(gpg *)",
        "WebFetch",
        "WebSearch",
    } <= deny
    sandbox = policy["sandbox"]
    assert sandbox == {
        "enabled": True,
        "failIfUnavailable": True,
        "autoAllowBashIfSandboxed": True,
        "allowUnsandboxedCommands": False,
        "excludedCommands": CONTROL_COMMANDS,
    }
    core = json.loads(CORE_POLICY.read_text(encoding="utf-8"))
    assert policy["hooks"] == core["hooks"]


def _template_record(tmp_path: Path) -> dict[str, object]:
    record = _record(
        tmp_path,
        "gas-city-template",
        "template-candidate",
        agents=["implementation-worker"],
        provider="claude",
        git_metadata=False,
    )
    record["control_policy"] = {
        "source": "templates/claude/template-candidate-control-policy.json",
        "sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
    }
    return record


def test_source_owned_template_profile_and_rendered_provider_are_narrow(
    tmp_path: Path,
) -> None:
    document = json.loads(PROFILE.read_text(encoding="utf-8"))
    assert document["schema"] == "gc.managed-rig-permissions.v2"
    assert len(document["rigs"]) == 1
    record = document["rigs"][0]
    assert record["name"] == "gas-city-template"
    assert record["repository_path"] == "/home/loucmane/gas-city-template"
    assert record["worktree_root"] == TEMPLATE_ROOT
    assert record["agents"] == ["implementation-worker"]
    assert record["git_metadata"] is False
    assert record["environment"] == {
        "PATH": "/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin"
    }
    assert record["toolchains"][0]["executable"]["sha256"] == hashlib.sha256(
        Path("/usr/bin/python3.12").read_bytes()
    ).hexdigest()
    assert record["control_policy"]["sha256"] == hashlib.sha256(POLICY.read_bytes()).hexdigest()

    result, output = _render(tmp_path, [_template_record(tmp_path)])
    assert result.returncode == 0, result.stderr
    fragment = tomllib.loads(output.read_text(encoding="utf-8"))
    assert set(fragment["providers"]) == {"claude-template-candidate"}
    (patch,) = fragment["patches"]["agent"]
    assert patch["provider"] == "claude-template-candidate"
    assert patch["option_defaults"]["permission_mode"] == "full-auto"
    assert patch["env"] == {"PATH": "/usr/bin:/bin"}
    choice = fragment["providers"]["claude-template-candidate"]["options_schema"][0][
        "choices"
    ][1]
    assert choice["flag_args"] == [
        "--settings",
        str(POLICY.resolve()),
        "--add-dir",
        str(Path(_template_record(tmp_path)["worktree_root"])),
    ]
    assert ".git" not in choice["flag_args"]


@pytest.mark.parametrize(
    "source,path",
    [
        (
            "templates/claude/./candidate-control-policy.json",
            OPERATIONS_POLICY,
        ),
        (
            "tests/fixtures/unknown-candidate-control-policy.json",
            UNKNOWN_POLICY,
        ),
    ],
    ids=["non-literal", "unknown"],
)
def test_candidate_policy_source_vocabulary_is_exact(
    tmp_path: Path, source: str, path: Path
) -> None:
    record = _template_record(tmp_path)
    record["control_policy"] = {
        "source": source,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    result, output = _render(tmp_path, [record])
    assert result.returncode == 3
    assert "not an authorized candidate control policy" in result.stderr
    assert not output.exists()


def test_operations_and_signing_source_mappings_remain_unchanged(tmp_path: Path) -> None:
    candidate = _template_record(tmp_path)
    candidate["control_policy"] = {
        "source": "templates/claude/candidate-control-policy.json",
        "sha256": hashlib.sha256(OPERATIONS_POLICY.read_bytes()).hexdigest(),
    }
    result, output = _render(tmp_path, [candidate])
    assert result.returncode == 0, result.stderr
    assert set(tomllib.loads(output.read_text(encoding="utf-8"))["providers"]) == {
        "claude-candidate"
    }

    signing = _record(
        tmp_path,
        "gascity",
        "signing",
        agents=["implementation-worker"],
        provider="claude",
    )
    signing["control_policy"] = {
        "source": "templates/claude/core-signing-control-policy.json",
        "sha256": hashlib.sha256(CORE_POLICY.read_bytes()).hexdigest(),
    }
    result, output = _render(tmp_path, [signing], name="signing.json")
    assert result.returncode == 0, result.stderr
    assert set(tomllib.loads(output.read_text(encoding="utf-8"))["providers"]) == {
        "claude-signing"
    }


def _normalized_shipped_render(tmp_path: Path, profile_path: Path) -> str:
    """Render a shipped record at disposable roots and normalize only those roots."""

    document = json.loads(profile_path.read_text(encoding="utf-8"))
    fixture = tmp_path / profile_path.stem
    vault = fixture / "classified-vault"
    vault.mkdir(parents=True)
    document["classified_vault"] = str(vault)
    replacements: dict[str, str] = {str(ROOT): "<TEMPLATE_ROOT>"}
    for index, record in enumerate(document["rigs"]):
        candidate = "operations-candidate-worker" in record["agents"]
        slot = "a-operations" if candidate else f"b-core-{index}"
        repository = fixture / f"repository-{slot}"
        worktree_root = fixture / f"worktrees-{slot}"
        (repository / ".git").mkdir(parents=True)
        worktree_root.mkdir()
        record["repository_path"] = str(repository)
        record["worktree_root"] = str(worktree_root)
        if candidate:
            replacements[str(repository)] = "<OPERATIONS_REPOSITORY>"
            replacements[str(worktree_root)] = "<OPERATIONS_WORKTREE_ROOT>"
        else:
            replacements[str(repository)] = "<CORE_REPOSITORY>"
            replacements[str(worktree_root)] = "<CORE_WORKTREE_ROOT>"
    registry = fixture / "registry.json"
    registry.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    city = fixture / "city"
    city.mkdir()
    output = city / "managed/rig-permissions.toml"
    environment = os.environ.copy()
    environment.update(
        {
            "GCT_SKIP_CONFIG_VALIDATION": "1",
            "GCT_TEST_ROOT": str(tmp_path.resolve()),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    completed = subprocess.run(
        [
            str(RENDERER),
            "--city",
            str(city),
            "--apply",
            "--registry",
            str(registry),
            "--output",
            str(output),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr
    rendered = output.read_text(encoding="utf-8")
    for actual, placeholder in sorted(
        replacements.items(), key=lambda item: len(item[0]), reverse=True
    ):
        rendered = rendered.replace(actual, placeholder)
    rendered = re.sub(
        r"(?m)^# registry_sha256=[0-9a-f]{64}$",
        "# registry_sha256=<REGISTRY_SHA256>",
        rendered,
    )
    return re.sub(r"managed-[0-9a-f]{16}", "<MANAGED_CHOICE>", rendered)


@pytest.mark.parametrize(
    "profile,golden",
    [
        (CORE_SIGNING_PROFILE, GOLDEN / "core-signing.toml"),
        (OPERATIONS_PROFILE, GOLDEN / "operations-candidate.toml"),
    ],
    ids=["core-signing", "operations-candidate"],
)
def test_existing_closed_lane_renders_match_e6195b1_golden_output(
    tmp_path: Path, profile: Path, golden: Path
) -> None:
    assert _normalized_shipped_render(tmp_path, profile) == golden.read_text(
        encoding="utf-8"
    )


def test_shipped_root_matches_wrapper_add_dir_at_the_template_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = json.loads(PROFILE.read_text(encoding="utf-8"))["rigs"][0]
    canonical_root = Path("/home/loucmane/gas-city-template")
    monkeypatch.setattr(template_worker, "_ROOT", canonical_root)
    assert record["worktree_root"] == str(template_worker.default_config().add_dirs[0])
    assert record["repository_path"] == str(canonical_root)


def _installed_template_wrapper(tmp_path: Path) -> tuple[Path, Path]:
    install_root = tmp_path / "installation"
    source_root = install_root / "gas-city-template"
    for relative in (
        "bin/gct-claude-template-candidate-worker",
        "lib/gct_claude_template_candidate_worker.py",
        "lib/gct_claude_signing_worker.py",
        "lib/gct_claude_subscription.py",
        "templates/claude/template-candidate-control-policy.json",
        "templates/claude/template-candidate-provider.toml",
    ):
        destination = source_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    claude = install_root / "gascity/bin/claude"
    claude.parent.mkdir(parents=True)
    claude.write_text("#!/bin/sh\nprintf '%s\\n' 'fixture claude'\n", encoding="utf-8")
    claude.chmod(0o755)
    policy = source_root / "templates/claude/template-candidate-control-policy.json"
    policy.chmod(0o600)
    return source_root / "bin/gct-claude-template-candidate-worker", policy


def _template_candidate_prototype(tmp_path: Path) -> dict[str, object]:
    prototype = _provisioning_prototype(tmp_path)
    profile = prototype["profiles"][0]
    assert isinstance(profile, dict)
    entrypoint, policy = _installed_template_wrapper(tmp_path)
    version = subprocess.run(
        [str(entrypoint), "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
        env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
    ).stdout.strip()
    candidate_root = tmp_path / "installation/gas-city-template-candidate-worktrees"
    candidate_root.mkdir()
    profile.update(
        {
            "name": "gas-city-template/gc.implementation-worker",
            "profile_kind": "candidate",
            "signer_identity": "none",
            "argv": [
                str(entrypoint),
                "--settings",
                str(policy),
                "--add-dir",
                str(candidate_root),
            ],
            "control_policy": {
                "path": str(policy),
                "sha256": hashlib.sha256(policy.read_bytes()).hexdigest(),
            },
            "provider": {
                "name": "claude",
                "path": str(entrypoint),
                "resolved_path": str(entrypoint),
                "sha256": hashlib.sha256(entrypoint.read_bytes()).hexdigest(),
                "version_args": ["--version"],
                "version": version,
            },
            "writable_roots": [str(candidate_root)],
        }
    )
    return prototype


def test_provisioner_publishes_template_candidate_and_runner_selects_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prototype = _template_candidate_prototype(tmp_path)
    result = _provision(tmp_path, prototype, "--apply", "--json")
    assert result.returncode == 0, result.stderr
    _runner, receipt_path = _installed_paths(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    (profile,) = receipt["profiles"]
    assert profile["name"] == "gas-city-template/gc.implementation-worker"
    assert profile["profile_kind"] == "candidate"
    assert profile["signer_identity"] == "none"
    assert profile["provider"]["name"] == "claude"

    module = runpy.run_path(str(RUNNER), run_name="template_candidate_runner")
    monkeypatch.setenv("GCT_CANARY_WORKER_PROFILE_JSON", json.dumps(profile))
    contract = module["load_worker_profile_contract"](required_kind="candidate")
    assert contract.name == profile["name"]
    assert contract.kind == "candidate"
    with pytest.raises(Exception, match="may not select each other"):
        module["load_worker_profile_contract"](required_kind="signing")
