"""ga-fsfg R1: the hooked seat can discharge delivery-class events without tracked writes.

Delivery commands (git commit/push, gh pr create/ready/merge) enqueue events whose
evidence is Git itself. PreToolUse lets exactly one well-formed `workflow.py
discharge --pending-id <id>` through the pending block only when that id names one
delivery-class event; PostToolUse fails closed if the event is still queued and
never enqueues the discharge itself.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from test_pretooluse_gates import POSTTOOLUSE, PRETOOLUSE, make_repo, payload, run_gate, write

WORKFLOW = "plugins/gas-city-workflow/scripts/workflow.py"


def hooked_repo(tmp_path: Path, *, in_progress: bool = True) -> Path:
    """READY task repo with a stub workflow entrypoint.

    PostToolUse recording needs an in-progress current-work record; PreToolUse
    readiness in this fixture does not, so pretool cases leave it out.
    """

    repo = make_repo(tmp_path, ready=True)
    write(repo / WORKFLOW, "# synthetic runtime, never executed by the gate\n")
    if in_progress:
        write(
            repo / ".aegis/state/current-work.json",
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "mode": "task",
                    "status": "in-progress",
                    "task": {"id": "103", "slug": "claude-runtime-adapter", "status": "in-progress"},
                    "branch": {"current": "feat/task-103-claude-runtime-adapter"},
                }
            ),
        )
    return repo


def queue(repo: Path) -> list[dict[str, object]]:
    path = repo / ".aegis/state/pending-tracking.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("events", [])


def set_queue(repo: Path, events: list[dict[str, object]]) -> None:
    write(repo / ".aegis/state/pending-tracking.json", json.dumps({"schema_version": "1.0.0", "events": events}))


def pending(event_id: str, kind: str) -> dict[str, object]:
    return {
        "id": event_id,
        "kind": kind,
        "handler": "bash:git",
        "evidence": "git commit -S -m proof",
        "mode": "strict",
        "task": {"id": "103", "slug": "claude-runtime-adapter"},
    }


def discharge_command(event_id: str) -> str:
    return f"python3 {WORKFLOW} discharge --root . --pending-id {event_id} --note recorded"


@pytest.mark.parametrize(
    "command,kind",
    [
        ("git commit -S -m 'feat: proof'", "delivery"),
        ("git -C . commit -qm proof", "delivery"),
        ("git push origin feat/task-103-claude-runtime-adapter", "delivery"),
        ("gh pr create --base main --head feat/task-103-claude-runtime-adapter --title t --body b", "delivery"),
        ("gh pr ready 12", "delivery"),
        ("gh pr merge 12 --merge", "delivery"),
        ("sed -i 's/a/b/' src/main.py", "mutation"),
        ("git add -A", "mutation"),
        ("python3 scripts/build.py", "mutation"),
    ],
)
def test_posttool_classifies_delivery_class_events(tmp_path: Path, command: str, kind: str) -> None:
    repo = hooked_repo(tmp_path)

    assert run_gate(POSTTOOLUSE, repo, payload("Bash", command=command)).returncode == 0

    events = queue(repo)
    assert len(events) == 1
    assert events[0]["kind"] == kind


def test_posttool_file_edits_are_mutation_class(tmp_path: Path) -> None:
    repo = hooked_repo(tmp_path)

    assert run_gate(POSTTOOLUSE, repo, payload("Write", file_path="src/new.py", content="x")).returncode == 0

    assert [event["kind"] for event in queue(repo)] == ["mutation"]


def test_pretool_allows_exact_delivery_discharge_through_pending_block(tmp_path: Path) -> None:
    repo = hooked_repo(tmp_path, in_progress=False)
    set_queue(repo, [pending("0123456789ab", "delivery")])

    blocked = run_gate(PRETOOLUSE, repo, payload("Bash", command="python3 scripts/build.py"))
    assert blocked.returncode == 2 and "pending S:W:H:E tracking" in blocked.stderr

    allowed = run_gate(PRETOOLUSE, repo, payload("Bash", command=discharge_command("0123456789ab")))
    assert allowed.returncode == 0, allowed.stderr


@pytest.mark.parametrize(
    "command",
    [
        discharge_command("abcdef012345"),
        discharge_command("0123456789ab") + " && python3 scripts/build.py",
        f"python3 {WORKFLOW} discharge --root /tmp/elsewhere --pending-id 0123456789ab --note recorded",
        f"python3 {WORKFLOW} discharge --root . --pending-id current --note recorded",
        f"python3 {WORKFLOW} discharge --root . --pending-id 0123456789ab",
        f"python3 {WORKFLOW} discharge --root . --pending-id 0123456789ab --note recorded --evidence proof",
    ],
)
def test_pretool_refuses_malformed_or_unmatched_discharge(tmp_path: Path, command: str) -> None:
    repo = hooked_repo(tmp_path, in_progress=False)
    set_queue(repo, [pending("0123456789ab", "delivery"), pending("abcdef012345", "mutation")])

    result = run_gate(PRETOOLUSE, repo, payload("Bash", command=command))

    assert result.returncode == 2
    assert '"permissionDecision": "allow"' not in result.stdout


def test_pretool_refuses_discharge_of_duplicate_ids(tmp_path: Path) -> None:
    repo = hooked_repo(tmp_path, in_progress=False)
    set_queue(repo, [pending("0123456789ab", "delivery"), pending("0123456789ab", "delivery")])

    assert run_gate(PRETOOLUSE, repo, payload("Bash", command=discharge_command("0123456789ab"))).returncode == 2


def test_posttool_discharge_fails_closed_while_event_remains(tmp_path: Path) -> None:
    repo = hooked_repo(tmp_path)
    set_queue(repo, [pending("0123456789ab", "delivery")])
    request = payload("Bash", command=discharge_command("0123456789ab"))

    result = run_gate(POSTTOOLUSE, repo, request)

    assert result.returncode == 2
    assert "discharge" in result.stderr
    assert [event["id"] for event in queue(repo)] == ["0123456789ab"]


def test_posttool_discharge_success_enqueues_nothing(tmp_path: Path) -> None:
    repo = hooked_repo(tmp_path)
    set_queue(repo, [pending("abcdef012345", "mutation")])
    request = payload("Bash", command=discharge_command("0123456789ab"))

    assert run_gate(POSTTOOLUSE, repo, request).returncode == 0

    assert [event["id"] for event in queue(repo)] == ["abcdef012345"]
