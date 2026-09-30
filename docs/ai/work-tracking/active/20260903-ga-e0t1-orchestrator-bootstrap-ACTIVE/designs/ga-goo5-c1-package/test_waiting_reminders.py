"""Offline protocol fixtures: unchanged validator, no model or runtime proof."""
import copy
import hashlib
import json
from pathlib import Path
import types

import pytest

HERE = Path(__file__).parent
OLD = HERE.parent / "ga-x2wz-c1-package"
VALIDATOR_SHA = "079702bacec3b79f6fea1dbcefd406936dd4f2d1a4055235d7a7b477c027fed6"


def module(path, sha=None):
    raw = path.read_bytes()
    if sha is not None:
        assert hashlib.sha256(raw).hexdigest() == sha
    value = types.ModuleType(path.stem)
    value.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), value.__dict__)
    return value


v = module(OLD / "startup-validation.py", VALIDATOR_SHA)
p = module(HERE / "waiting-prompt.py")
SESSION = {"id": "ci-fixture", "created_at": "2026-09-29T12:00:00Z",
           "last_active": "2026-09-29T12:00:07+00:00"}
REPORT = "a" * 64
PROBE = "b" * 64
MARKER = ("WAITING FOR SOURCE RELEASE: ga-x2wz session=ci-fixture report_sha256="
          + REPORT + " probe_sha256=" + PROBE)
PROSE = ("ga-x2wz is already claimed by session ci-fixture. Startup passed; "
         "waiting for the exact same-session SOURCE RELEASE before further work.")
REMINDER = ("<system-reminder>\nYou have a deferred reminder that was queued until "
            "a safe boundary:\n\n- [session] check for assigned work\n\n"
            "Handle them after this turn.\n</system-reminder>")


def final(text, second):
    return [
        {"type": "response_item", "timestamp": f"2026-09-29T12:00:{second:02d}.000Z",
         "payload": {"type": "message", "role": "assistant", "phase": "final_answer",
                     "content": [{"type": "output_text", "text": text}]}},
        {"type": "event_msg", "timestamp": f"2026-09-29T12:00:{second:02d}.100Z",
         "payload": {"type": "task_complete", "last_agent_message": text,
                     "turn_id": f"fixture-{second}"}},
    ]


def rows(last=MARKER):
    return [{"type": "session_meta", "payload": {"id": "fixture-provider"}}] + final(MARKER, 5) + [
        {"type": "response_item", "timestamp": "2026-09-29T12:00:06.000Z",
         "payload": {"type": "message", "role": "user",
                     "content": [{"type": "input_text", "text": REMINDER}]}}
    ] + final(last, 7)


def wire(records):
    return ("\n".join(json.dumps(row) for row in records) + "\n").encode()


def validate(raw, **kwargs):
    return v.waiting_turn(raw, kwargs.get("session", SESSION),
                          kwargs.get("report", REPORT), kwargs.get("probe", PROBE),
                          kwargs.get("observed", "2026-09-29T12:00:08Z"))


def test_exact_observed_failure_still_refuses():
    with pytest.raises(RuntimeError, match="not exact waiting marker"):
        validate(wire(rows(PROSE)))


@pytest.mark.parametrize("count", [1, 2, 4])
def test_repeated_completed_exact_markers_pass_without_authority(count):
    records = rows()
    for index in range(1, count):
        records += copy.deepcopy(records[3:4]) + final(MARKER, 7 + index)
    latest = dict(SESSION, last_active=f"2026-09-29T12:00:{6 + count:02d}+00:00")
    proof = validate(wire(records), session=latest, observed="2026-09-29T12:00:20Z")
    assert proof["completed_waiting_turn"] is True
    assert proof["source_release_authorized_by_this_check"] is False


@pytest.mark.parametrize("kind", [
    "missing-completion", "wrong-task", "wrong-session", "wrong-report",
    "wrong-probe", "partial-line", "markdown", "activity-after-final",
    "future-completion", "wrong-completion-marker", "stale-activity",
])
def test_existing_fail_closed_contract_is_not_relaxed(kind):
    records = rows()
    if kind == "missing-completion":
        records.pop()
    elif kind == "activity-after-final":
        records.append({"type": "event_msg", "payload": {"type": "task_started"}})
    elif kind == "future-completion":
        records[-1]["timestamp"] = "2026-09-29T12:00:09.000Z"
    elif kind == "wrong-completion-marker":
        records[-1]["payload"]["last_agent_message"] = PROSE
    elif kind not in ("partial-line", "stale-activity"):
        before, after = {
            "wrong-task": ("ga-x2wz", "ga-other"),
            "wrong-session": ("ci-fixture", "ci-other"),
            "wrong-report": (REPORT, "c" * 64),
            "wrong-probe": (PROBE, "c" * 64),
            "markdown": (MARKER, "`" + MARKER + "`"),
        }[kind]
        records[-2]["payload"]["content"][0]["text"] = MARKER.replace(before, after)
    raw = wire(records)
    if kind == "partial-line":
        raw = raw[:-1]
    with pytest.raises(RuntimeError):
        validate(raw, session=dict(SESSION, last_active="2026-09-29T12:00:06+00:00")
                 if kind == "stale-activity" else SESSION)


def test_prompt_delta_is_one_insertion_and_covers_transport_and_drain():
    raw = (OLD / "PRECLAIM.md").read_bytes()
    corrected = p.corrected(raw)
    assert corrected.replace(p.INSERTION.encode(), b"", 1) == raw
    assert corrected.count(p.INSERTION.encode()) == 1
    assert b"sole final answer" in corrected
    assert b"no new tool call" in corrected
    assert b"inside Core's deferred-reminder" in corrected
    assert b"drain or containment takes precedence" in corrected
    assert b"never reopen" in corrected
    with pytest.raises(ValueError, match="predecessor mismatch"):
        p.corrected(raw + b"\n")
