"""ga-fsfg R1: journal-bound discharge of delivery-class pending events.

A commit, push or PR operation enqueues a strict pending event whose durable
evidence is Git itself. `discharge` records that event into the workflow journal
and removes it from the queue without rewriting any tracked S:W:H:E surface, so a
hooked seat can reach a clean tree with an empty queue and publish.
"""

import json

import pytest

from test_workflow_coordinate import lane  # noqa: F401 - shared real-Git fixture
from workflow import parse_args
from workflow_common import WorkflowError
from workflow_discharge import discharge


def _queue(root, events):
    path = root / ".aegis/state/pending-tracking.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": "1.0.0", "events": events}))
    return path


def _event(event_id, kind, handler="bash:git", evidence="git commit -S -m proof"):
    return {
        "id": event_id,
        "kind": kind,
        "handler": handler,
        "evidence": evidence,
        "mode": "strict",
        "created_at": "2026-09-14T12:00:00Z",
        "task": {"id": "ga-test", "slug": "fixture"},
    }


def test_discharge_records_delivery_event_in_journal_and_clears_queue(lane):  # noqa: F811
    root, registry, runner, path = lane
    queue = _queue(root, [_event("0123456789ab", "delivery"), _event("abcdef012345", "mutation", "edit", "src/x.py")])

    result = discharge(root, "0123456789ab", "Recorded the signed commit", runner, registry=registry)

    assert result["status"] == "recorded" and result["pending_id"] == "0123456789ab"
    assert len(result["head"]) == 40 and len(result["tree"]) == 40
    events = json.loads(path.read_text())["events"]
    assert events[-1]["action"] == "discharge" and events[-1]["status"] == "recorded"
    assert events[-1]["pending_id"] == "0123456789ab"
    assert events[-1]["handler"] == "bash:git" and events[-1]["evidence"] == "git commit -S -m proof"
    assert events[-1]["head"] == result["head"] and events[-1]["note"] == "Recorded the signed commit"
    assert [event["id"] for event in json.loads(queue.read_text())["events"]] == ["abcdef012345"]


def test_discharge_refuses_missing_duplicate_or_non_delivery_events(lane):  # noqa: F811
    root, registry, runner, path = lane
    _queue(
        root,
        [
            _event("0123456789ab", "delivery"),
            _event("0123456789ab", "delivery"),
            _event("abcdef012345", "mutation", "edit", "src/x.py"),
        ],
    )
    with pytest.raises(WorkflowError, match="exactly one"):
        discharge(root, "0123456789ab", "twice", runner, registry=registry)
    with pytest.raises(WorkflowError, match="exactly one"):
        discharge(root, "0000000000aa", "absent", runner, registry=registry)
    with pytest.raises(WorkflowError, match="delivery-class"):
        discharge(root, "abcdef012345", "an edit", runner, registry=registry)
    assert not json.loads(path.read_text()).get("events")
    assert len(json.loads((root / ".aegis/state/pending-tracking.json").read_text())["events"]) == 3


@pytest.mark.parametrize("pending_id", ["", "current", "latest", "ABCDEFABCDEF", "abc123"])
def test_discharge_refuses_nonliteral_identifiers_before_any_work(lane, pending_id):  # noqa: F811
    root, registry, runner, _ = lane
    before = len(runner.calls)
    with pytest.raises(WorkflowError, match="pending event identity"):
        discharge(root, pending_id, "note", runner, registry=registry)
    assert len(runner.calls) == before


def test_discharge_and_compact_parsers_are_closed():
    parsed = parse_args(["discharge", "--root", "/tmp/target", "--pending-id", "0123456789ab", "--note", "done"])
    assert parsed.command == "discharge" and parsed.pending_id == "0123456789ab"
    with pytest.raises(SystemExit):
        parse_args(["discharge", "--root", "/tmp/target", "--note", "done"])
    with pytest.raises(SystemExit):
        parse_args(["discharge", "--root", "/tmp/target", "--pending-id", "0123456789ab"])
    with pytest.raises(SystemExit):
        parse_args(["discharge", "--root", "/tmp/target", "--pending-id", "0123456789ab", "--note", "n", "--evidence", "e"])
    assert parse_args(["compact-journal", "--root", "/tmp/target"]).command == "compact-journal"
    with pytest.raises(SystemExit):
        parse_args(["compact-journal", "--root", "/tmp/target", "--apply"])
