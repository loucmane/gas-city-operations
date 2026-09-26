"""ga-fsfg R4: the `dispatch` coordination action in the executor.

Real Git, scaffold, journal and ownership, and the gate's own validated profile loader
over a fixture seat; a fake scoped gc answers the Beads, `bd ready`, `agent list` and
the sling. No test reads the live profile or touches a live store.
"""

import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from test_gas_city_workflow_transitions import _fixture_project, _run, begin
from test_workflow_coordinate import LedgerRunner

import workflow_dispatch  # noqa: E402 - the transitions module puts the scripts on sys.path.
from workflow import parse_args
from workflow_common import CommandRunner, WorkflowError
from workflow_coordinate import coordinate, log

PROFILE = Path(".claude/orchestrator-command-profile.json")
GC = "/home/loucmane/gascity/bin/gc"
CITY = "/home/loucmane/gascity/city"
RIG = "future-project"
TARGET = "future-project/worker"
PREROUTE = "future-project/operations-candidate-worker"
# The reviewed ga-6utp environment, pinned literally: exactly six variables.
ENVIRONMENT = {
    "HOME": "/home/loucmane",
    "PATH": "/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin",
    "GC_HOME": "/home/loucmane/gascity/home",
    "GIT_OPTIONAL_LOCKS": "0",
    "BD_DISABLE_METRICS": "1",
    "LANG": "C",
}


class Clock:
    def __init__(self):
        self.now = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


class DispatchRunner(LedgerRunner):
    """LedgerRunner plus the timed dispatch gc calls, recorded with env and timeout."""

    def __init__(self, clock):
        super().__init__()
        self.clock = clock
        self.timed = []
        self.sling_times = []
        self.sling_modes = []
        self.not_ready = set()
        self.oversized = None
        self.agents = [
            {"qualified_name": TARGET, "suspended": False},
            {"name": "operations-candidate-worker", "rig": RIG, "suspended": False},
        ]

    def run(self, argv, *, cwd=None, env=None, check=True, timeout=None):
        args = list(argv)
        if timeout is None:
            return super().run(args, cwd=cwd, env=env, check=check)
        self.timed.append((args, dict(env or {}), timeout))
        if args[5:7] == ["bd", "show"]:
            kind, out = "show", json.dumps([self.beads[args[7]]])
        elif args[5:7] == ["bd", "ready"]:
            ready = [
                bead
                for bead in self.beads.values()
                if bead.get("status") == "open" and bead["id"] not in self.not_ready
            ]
            kind, out = "ready", json.dumps(ready)
        elif args[3:5] == ["agent", "list"]:
            kind, out = "agent", json.dumps(self.agents)
        elif args[5] == "sling":
            kind, out = "sling", self._sling(args[6], args[7])
        else:
            raise AssertionError(f"unexpected timed call: {args}")
        if self.oversized == kind:
            cap = 16 * 1024 * 1024 if kind == "ready" else 1024 * 1024
            out += " " * cap
        return subprocess.CompletedProcess(args, 0, out, "")

    def _sling(self, target, bead_id):
        self.sling_times.append(self.clock.now)
        mode = self.sling_modes.pop(0) if self.sling_modes else "route"
        bead = self.beads[bead_id]
        if mode not in {"timeout", "not-json"}:
            bead.setdefault("metadata", {})["gc.routed_to"] = target
            bead["updated_at"] = "2030-01-01T12:00:01Z"
        metadata = bead.get("metadata", {})
        if mode == "claim":
            bead.update(status="in_progress", assignee="worker-1", started_at="2030-01-01T12:00:02Z")
            metadata.update(
                {
                    "gc.session_id": "ci-abc12",
                    "gc.session_name": "worker-ci-abc12",
                    "gc.work_branch": "agent/rig-checkout",
                }
            )
        elif mode == "partial-claim":
            bead["assignee"] = "worker-1"
        elif mode == "extra-key":
            metadata["gc.work_dir"] = "/tmp/elsewhere"
        elif mode == "title":
            bead["title"] = "rewritten"
        elif mode == "closed":
            bead["status"] = "closed"
        if mode in {"timeout", "land-timeout"}:
            raise WorkflowError("command timed out after 30 s: gc sling")
        if mode == "not-json":
            return "routed\n"
        result = {
            "schema_version": "1",
            "success": mode != "unsuccessful",
            "routed": True,
            "dry_run": False,
            "bead_id": bead_id,
            "target": target,
        }
        if mode == "convoy":
            result["convoy_id"] = "cv-1"
        if mode == "molecule":
            result["molecule_id"] = "mol-1"
        return json.dumps(result)

    def slings(self):
        return [args for args, _, _ in self.timed if args[5:6] == ["sling"]]


@dataclass
class Lane:
    seat: Path
    root: Path
    registry: Path
    runner: DispatchRunner
    journal: Path
    child: str
    clock: Clock

    def dispatch(self, bead=None, target=TARGET, **extra):
        return coordinate(
            self.root,
            bead or self.child,
            "dispatch",
            {"target": target, **extra},
            self.runner,
            registry=self.registry,
            seat=self.seat,
        )

    def records(self):
        return json.loads(self.journal.read_text()).get("coordination", {})

    def dispatch_records(self):
        return [r for r in self.records().values() if r["request"]["action"] == "dispatch"]

    def edit_journal(self, change):
        data = json.loads(self.journal.read_text())
        change(data)
        self.journal.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def seat_profile(seat, **changes):
    value = {
        "schema": "aegis.claude-orchestrator-command-profile.v1",
        "project_id": "future-project",
        "canonical_root": str(seat),
        "worktree_root": str(seat.parent / "future-project-worktrees"),
        "city": CITY,
        "rig": RIG,
        "commands": ["workflow-coordinate", "dispatch"],
        "dispatch_targets": [TARGET],
        "preroute_targets": [PREROUTE],
    }
    value.update(changes)
    return {key: item for key, item in value.items() if item is not None}


def commit_profile(seat, value):
    (seat / PROFILE).write_text(json.dumps(value))
    _run(seat, "git", "add", str(PROFILE))
    _run(seat, "git", "commit", "-qm", "orchestrator profile")


def make_lane(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "no-host-config"))
    clock = Clock()
    monkeypatch.setattr(workflow_dispatch, "_clock", clock)
    seat, registry = _fixture_project(tmp_path)
    _run(seat, "git", "remote", "add", "origin", "git@github.com:fixture/future-project.git")
    commit_profile(seat, seat_profile(seat))
    runner = DispatchRunner(clock)
    result = begin(seat, "ga-test", slug="fixture", goals=[], registry=registry, runner=runner)
    root = Path(result["spec"]["worktree"])
    created = coordinate(
        root,
        "ga-test",
        "create",
        {"title": "Routed child", "description": "Scope", "acceptance": "Proof"},
        runner,
        registry=registry,
    )
    return Lane(seat, root, registry, runner, Path(result["journal"]), created["bead_id"], clock)


@pytest.fixture
def lane(tmp_path, monkeypatch):
    return make_lane(tmp_path, monkeypatch)


def show(bead):
    return [GC, "--city", CITY, "--rig", RIG, "bd", "show", bead, "--json"]


def sling(bead, target=TARGET):
    return [GC, "--city", CITY, "--rig", RIG, "sling", target, bead, "--no-formula", "--no-convoy", "--json"]


READY = [GC, "--city", CITY, "--rig", RIG, "bd", "ready", "--limit", "0", "--json"]
AGENTS = [GC, "--city", CITY, "agent", "list", "--json"]


# --- The action -----------------------------------------------------------------------


def test_dispatch_routes_the_created_child_with_the_exact_argv_and_environment(lane):
    result = lane.dispatch()

    assert result["status"] == "applied" and result["slung"] is True
    assert result["bead_id"] == lane.child == "ga-test.1" and result["target"] == TARGET
    [record] = lane.dispatch_records()
    assert record["state"] == "verified" and record["result_bead"] == lane.child
    assert record["request"] == {
        "bead_id": lane.child,
        "action": "dispatch",
        "fields": {"target": TARGET},
    }
    assert record["last_sling_at"] == "2030-01-01T12:00:00.000000Z"
    assert [argv for argv, _, _ in lane.runner.timed] == [
        show(lane.child),
        READY,
        AGENTS,
        show(lane.child),
        sling(lane.child),
        show(lane.child),
    ]
    for _argv, env, timeout in lane.runner.timed:
        assert env == ENVIRONMENT and timeout == 30
    assert workflow_dispatch.ENVIRONMENT == ENVIRONMENT
    assert workflow_dispatch.ENVIRONMENT["BD_DISABLE_METRICS"] == "1"
    assert lane.runner.beads[lane.child]["metadata"] == {"gc.routed_to": TARGET}
    # The inherited ownership reads keep managed_environment(): never timed, never this env.
    assert all(show("ga-test") != argv for argv, _, _ in lane.runner.timed)


def test_replaying_a_completed_dispatch_after_the_child_changed_is_a_noop(lane):
    lane.dispatch()
    child = lane.runner.beads[lane.child]
    child.update(status="in_progress", assignee="worker-1", notes="worker progress")
    calls = len(lane.runner.timed)

    replay = lane.dispatch()

    assert replay["status"] == "unchanged" and replay["bead_id"] == lane.child
    assert len(lane.runner.timed) == calls  # no live read of the child, no second sling
    assert len(lane.runner.slings()) == 1


def test_log_discharges_after_a_dispatch_and_a_later_note_succeeds(lane):
    lane.dispatch()
    result = log(lane.root, None, "Recorded the dispatch", lane.runner, pending_id="0123456789ab")
    assert result["status"] == "applied" and result["pending_id"] == "0123456789ab"
    note = coordinate(
        lane.root, "ga-test", "note", {"text": "Routed the child"}, lane.runner, registry=lane.registry
    )
    assert note["status"] == "applied"


@pytest.mark.parametrize("mode", ["claim", "partial-claim"])
def test_a_claim_racing_the_readback_is_an_accepted_delta(lane, mode):
    lane.runner.sling_modes = [mode]
    result = lane.dispatch()
    assert result["status"] == "applied"
    [record] = lane.dispatch_records()
    assert record["state"] == "verified"


def test_the_readback_delta_rules():
    before = {
        "id": "ga-x.1",
        "title": "t",
        "status": "open",
        "metadata": {"owner.note": "kept"},
        "dependencies": [{"id": "ga-x", "status": "in_progress"}],
        "updated_at": "a",
    }
    route = {**before, "metadata": {"owner.note": "kept", "gc.routed_to": TARGET}, "updated_at": "b"}
    claim = {
        **route,
        "status": "in_progress",
        "assignee": "w",
        "started_at": "c",
        "metadata": {
            **route["metadata"],
            "gc.session_id": "s",
            "gc.session_name": "n",
            "gc.work_branch": "agent/x",
        },
    }
    assert workflow_dispatch.routed(before, route, TARGET)
    assert workflow_dispatch.routed(before, claim, TARGET)
    assert not workflow_dispatch.routed(before, route, "future-project/other")
    assert not workflow_dispatch.routed(before, before, TARGET)
    for bad in (
        {**claim, "status": "closed"},
        {**claim, "title": "changed"},
        {**claim, "labels": ["new"]},
        {**claim, "metadata": {**claim["metadata"], "gc.work_dir": "/w"}},
        {**claim, "metadata": {"gc.routed_to": TARGET}},
        {**claim, "dependencies": [{"id": "ga-x", "status": "closed"}]},
        {key: value for key, value in claim.items() if key != "title"},
    ):
        assert not workflow_dispatch.routed(before, bad, TARGET)
    # A claim field is added or changed, never removed.
    assert not workflow_dispatch.routed({**before, "started_at": "x"}, route, TARGET)


# --- Refusals before any sling --------------------------------------------------------


def _child(lane, bead_id, **fields):
    bead = json.loads(json.dumps(lane.runner.beads[lane.child]))
    bead.update(id=bead_id, **fields)
    lane.runner.beads[bead_id] = bead
    return bead


def _record(lane, action, result_bead):
    def change(data):
        data["coordination"][action[0] * 64] = {
            "state": "verified",
            "request": {"bead_id": "ga-test", "action": action, "fields": {}},
            "result_bead": result_bead,
            "before": {"id": "ga-test"},
            "after": {"id": "ga-test"},
            "blocker_before": None,
        }

    lane.edit_journal(change)


REFUSALS = {
    "primary": (lambda lane: lane.dispatch(bead="ga-test"), "never an owned"),
    "malformed": (lambda lane: lane.dispatch(bead="GA-TEST.1"), "invalid coordination bead"),
    "inline-text": (
        lambda lane: lane.dispatch(bead="route the child please"),
        "invalid coordination bead",
    ),
    "no-create-record": (
        lambda lane: (_child(lane, "ga-test.2"), lane.dispatch(bead="ga-test.2")),
        "no verified create record",
    ),
    "note-record": (
        lambda lane: (
            _child(lane, "ga-test.3"),
            _record(lane, "note", "ga-test.3"),
            lane.dispatch(bead="ga-test.3"),
        ),
        "no verified create record",
    ),
    "depend-record": (
        lambda lane: (
            _child(lane, "ga-test.4"),
            _record(lane, "depend", "ga-test.4"),
            lane.dispatch(bead="ga-test.4"),
        ),
        "no verified create record",
    ),
    "not-dotted": (
        lambda lane: (
            _child(lane, "ga-zzz.1"),
            _record(lane, "create", "ga-zzz.1"),
            lane.dispatch(bead="ga-zzz.1"),
        ),
        "not a dotted child",
    ),
    "closed": (
        lambda lane: (lane.runner.beads[lane.child].update(status="closed"), lane.dispatch()),
        "open child",
    ),
    "assigned": (
        lambda lane: (lane.runner.beads[lane.child].update(assignee="someone"), lane.dispatch()),
        "assigned",
    ),
    "owned": (
        lambda lane: (
            lane.runner.beads[lane.child]["metadata"].update(
                {"workflow.external_owner": "external-coordinator.v1:x"}
            ),
            lane.dispatch(),
        ),
        "externally owned",
    ),
    "routed": (
        lambda lane: (
            lane.runner.beads[lane.child]["metadata"].update({"gc.routed_to": TARGET}),
            lane.dispatch(),
        ),
        "gc.. metadata",
    ),
    "work-dir": (
        lambda lane: (
            lane.runner.beads[lane.child]["metadata"].update({"gc.work_dir": "/w"}),
            lane.dispatch(),
        ),
        "gc.. metadata",
    ),
    "work-pack": (
        lambda lane: (
            lane.runner.beads[lane.child]["metadata"].update({"window.work_pack": "p"}),
            lane.dispatch(),
        ),
        "work-pack or workspace",
    ),
    "route-label": (
        lambda lane: (lane.runner.beads[lane.child].update(labels=["pool:w"]), lane.dispatch()),
        "route labels",
    ),
    "not-ready": (
        lambda lane: (lane.runner.not_ready.add(lane.child), lane.dispatch()),
        "bd ready does not list it",
    ),
    "unlisted-target": (
        lambda lane: lane.dispatch(target="future-project/other"),
        "not listed in dispatch_targets",
    ),
    "other-rig-target": (
        lambda lane: lane.dispatch(target="gascity/worker"),
        "not listed in dispatch_targets",
    ),
    "suspended": (
        lambda lane: (lane.runner.agents[0].update(suspended=True), lane.dispatch()),
        "suspended",
    ),
    "suspension-unknown": (
        lambda lane: (lane.runner.agents[0].pop("suspended"), lane.dispatch()),
        "suspended",
    ),
    "absent-agent": (
        lambda lane: (lane.runner.agents.pop(0), lane.dispatch()),
        "not exactly one agent",
    ),
    "canonical-workdir": (
        lambda lane: (lane.runner.agents[0].update(work_dir=str(lane.seat)), lane.dispatch()),
        "canonical checkout",
    ),
    "oversized-show": (
        lambda lane: (setattr(lane.runner, "oversized", "show"), lane.dispatch()),
        "bd show output exceeds",
    ),
    "oversized-ready": (
        lambda lane: (setattr(lane.runner, "oversized", "ready"), lane.dispatch()),
        "bd ready output exceeds",
    ),
    "oversized-agent-list": (
        lambda lane: (setattr(lane.runner, "oversized", "agent"), lane.dispatch()),
        "agent list output exceeds",
    ),
    "extra-argument": (
        lambda lane: lane.dispatch(text="also a note"),
        "overbroad",
    ),
}


@pytest.mark.parametrize("case", sorted(REFUSALS))
def test_dispatch_refuses_before_any_sling(lane, case):
    action, match = REFUSALS[case]
    with pytest.raises(WorkflowError, match=match):
        action(lane)
    assert lane.runner.slings() == []
    assert lane.dispatch_records() == []


def test_an_attached_bead_is_never_dispatched(lane):
    coordinate(lane.root, "ga-test", "depend", {"blocker": "ga-other"}, lane.runner, registry=lane.registry)
    with pytest.raises(WorkflowError, match="never an owned"):
        lane.dispatch(bead="ga-other")
    assert lane.runner.slings() == []


@pytest.mark.parametrize(
    "action,fields",
    [
        ("note", {"text": "x"}),
        ("create", {"title": "t", "description": "d", "acceptance": "a"}),
        ("depend", {"blocker": "ga-other"}),
    ],
)
def test_the_exemption_never_opens_other_actions_on_the_unowned_child(lane, action, fields):
    with pytest.raises(WorkflowError, match="not owned"):
        coordinate(lane.root, lane.child, action, fields, lane.runner, registry=lane.registry)


@pytest.mark.parametrize(
    "changes,match",
    [
        # dispatch_targets without dispatch in commands.
        ({"commands": ["workflow-coordinate"]}, "require dispatch in commands"),
        ({"preroute_targets": None}, "requires dispatch_targets and preroute_targets"),
        ({"preroute_targets": []}, "non-empty closed list"),
        ({"dispatch_targets": ["gascity/worker"]}, "agent of the profile rig"),
        ({"commands": ["dispatch"]}, "requires workflow-coordinate"),
    ],
)
def test_an_invalid_profile_refuses_every_dispatch(tmp_path, monkeypatch, changes, match):
    lane = make_lane(tmp_path, monkeypatch)
    commit_profile(lane.seat, seat_profile(lane.seat, **changes))
    with pytest.raises(WorkflowError, match=match):
        lane.dispatch()
    assert lane.runner.slings() == []


def test_a_profile_without_dispatch_refuses_it(tmp_path, monkeypatch):
    lane = make_lane(tmp_path, monkeypatch)
    commit_profile(
        lane.seat,
        seat_profile(
            lane.seat, commands=["workflow-coordinate"], dispatch_targets=None, preroute_targets=None
        ),
    )
    with pytest.raises(WorkflowError, match="not opted into"):
        lane.dispatch()


def test_a_preroute_lane_is_never_dispatched(tmp_path, monkeypatch):
    lane = make_lane(tmp_path, monkeypatch)
    commit_profile(lane.seat, seat_profile(lane.seat, dispatch_targets=[TARGET, PREROUTE]))
    with pytest.raises(WorkflowError, match="reviewed window package"):
        lane.dispatch(target=PREROUTE)
    assert lane.runner.slings() == []


def test_a_worktree_of_another_project_refuses(tmp_path, monkeypatch):
    """A registered-project or review-project <W> is not an Operations worktree."""

    lane = make_lane(tmp_path, monkeypatch)
    (tmp_path / "other").mkdir()
    other = make_lane(tmp_path / "other", monkeypatch)
    with pytest.raises(WorkflowError, match="requires an Operations worktree"):
        coordinate(
            other.root,
            other.child,
            "dispatch",
            {"target": TARGET},
            other.runner,
            registry=other.registry,
            seat=lane.seat,
        )
    assert other.runner.slings() == []


def test_the_profile_comes_from_the_canonical_seat_only(lane):
    with pytest.raises(WorkflowError, match="does not belong to the canonical runtime"):
        workflow_dispatch.load_profile(lane.root)
    (lane.seat / PROFILE).unlink()
    with pytest.raises(WorkflowError, match="requires the orchestrator command profile"):
        workflow_dispatch.load_profile(lane.seat)


def test_a_loader_exception_becomes_a_workflow_error(lane):
    (lane.seat / PROFILE).write_text("{not json")
    with pytest.raises(WorkflowError, match="cannot load the orchestrator profile"):
        workflow_dispatch.load_profile(lane.seat)


def test_the_runtime_seat_is_the_git_common_directory_parent(lane, monkeypatch):
    """Derived from the runtime the executor runs from, never a hard-coded path."""

    monkeypatch.setattr(workflow_dispatch, "workflow_runtime_root", lambda: lane.root)
    assert workflow_dispatch._runtime_seat() == lane.seat
    assert workflow_dispatch.load_profile()["canonical_root"] == str(lane.seat)


def test_the_city_and_rig_must_equal_the_profile(lane, monkeypatch):
    import project_context

    real = project_context.build_context

    def other_rig(root, registry):
        context = real(root, registry)
        context["workflow"]["rig"] = "gascity"
        return context

    monkeypatch.setattr("workflow_coordinate.build_context", other_rig)
    with pytest.raises(WorkflowError, match="city and rig"):
        lane.dispatch()


def test_the_cli_parser_accepts_only_the_dispatch_form():
    parsed = parse_args(
        ["coordinate", "--root", "/w", "--bead", "ga-x.1", "--action", "dispatch", "--target", TARGET]
    )
    assert parsed.action == "dispatch" and parsed.target == TARGET
    with pytest.raises(SystemExit):
        parse_args(["coordinate", "--root", "/w", "--bead", "ga-x.1", "--action", "route"])
    with pytest.raises(SystemExit):
        parse_args(
            ["coordinate", "--root", "/w", "--bead", "ga-x.1", "--action", "dispatch", "--force"]
        )


# --- The sling and its readback -------------------------------------------------------


@pytest.mark.parametrize(
    "mode,match",
    [
        ("extra-key", "not an accepted route and claim delta"),
        ("title", "not an accepted route and claim delta"),
        ("closed", "not an accepted route and claim delta"),
        ("convoy", "one plain route"),
        ("molecule", "one plain route"),
        ("unsuccessful", "one plain route"),
        ("not-json", "invalid JSON"),
        ("timeout", "timed out"),
    ],
)
def test_a_failed_sling_or_readback_leaves_the_intent_pending(lane, mode, match):
    lane.runner.sling_modes = [mode]
    with pytest.raises(WorkflowError, match=match):
        lane.dispatch()
    [record] = lane.dispatch_records()
    assert record["state"] == "pending" and len(lane.runner.slings()) == 1


def test_an_oversized_sling_result_leaves_the_intent_pending(lane):
    lane.runner.oversized = "sling"
    with pytest.raises(WorkflowError, match="sling output exceeds"):
        lane.dispatch()
    [record] = lane.dispatch_records()
    assert record["state"] == "pending"


# --- Completing a pending dispatch ----------------------------------------------------


def test_a_pending_dispatch_whose_child_is_routed_completes_without_a_second_sling(lane):
    lane.runner.sling_modes = ["land-timeout"]
    with pytest.raises(WorkflowError, match="timed out"):
        lane.dispatch()
    lane.runner.beads[lane.child].update(status="in_progress", assignee="worker-1")
    lane.clock.advance(5)

    result = lane.dispatch()

    assert result["status"] == "applied" and result["slung"] is False
    assert len(lane.runner.slings()) == 1
    [record] = lane.dispatch_records()
    assert record["state"] == "verified"


def test_a_pending_dispatch_whose_child_is_untouched_slings_once_more(lane):
    lane.runner.sling_modes = ["timeout"]
    with pytest.raises(WorkflowError, match="timed out"):
        lane.dispatch()
    lane.runner.beads[lane.child]["updated_at"] = "2030-01-01T12:00:30Z"
    lane.clock.advance(61)

    result = lane.dispatch()

    assert result["status"] == "applied" and result["slung"] is True
    assert len(lane.runner.slings()) == 2
    [record] = lane.dispatch_records()
    assert record["state"] == "verified"
    assert record["last_sling_at"] == "2030-01-01T12:01:01.000000Z"


def test_two_resling_timeouts_never_sling_within_60_seconds_of_each_other(lane):
    lane.runner.sling_modes = ["timeout", "timeout", "timeout"]
    with pytest.raises(WorkflowError, match="timed out"):
        lane.dispatch()
    # Seconds after the first sling: 30 refuses, 61 re-slings (timeout), 120 refuses,
    # 121 re-slings (timeout), 180 refuses; 181 re-slings and lands.
    for step, outcome in ((30, "less than 60 s"), (31, "timed out"), (59, "less than 60 s")):
        lane.clock.advance(step)
        with pytest.raises(WorkflowError, match=outcome):
            lane.dispatch()
    for step, outcome in ((1, "timed out"), (59, "less than 60 s")):
        lane.clock.advance(step)
        with pytest.raises(WorkflowError, match=outcome):
            lane.dispatch()
    lane.clock.advance(1)
    assert lane.dispatch()["status"] == "applied"
    times = lane.runner.sling_times
    assert [int((moment - times[0]).total_seconds()) for moment in times] == [0, 61, 121, 181]
    assert all(later - earlier >= timedelta(seconds=60) for earlier, later in zip(times, times[1:]))


def test_a_failed_last_sling_at_write_refuses_without_slinging(lane, monkeypatch):
    real = workflow_dispatch.atomic_write_json
    writes = []

    def failing_second(path, journal):
        writes.append(path)
        if len(writes) == 2:
            raise OSError("disk full")
        real(path, journal)

    monkeypatch.setattr(workflow_dispatch, "atomic_write_json", failing_second)
    with pytest.raises(WorkflowError, match="no sling was sent"):
        lane.dispatch()
    assert lane.runner.slings() == []
    [record] = lane.dispatch_records()
    assert record["state"] == "pending" and record["last_sling_at"] == "2030-01-01T12:00:00.000000Z"

    # The completion's stamp write fails too: still no sling.
    lane.clock.advance(61)
    writes.clear()
    writes.append("already one")
    with pytest.raises(WorkflowError, match="no sling was sent"):
        lane.dispatch()
    assert lane.runner.slings() == []


def test_a_child_closed_while_its_dispatch_is_pending_stays_pending(lane):
    lane.runner.sling_modes = ["timeout"]
    with pytest.raises(WorkflowError, match="timed out"):
        lane.dispatch()
    lane.runner.beads[lane.child]["status"] = "closed"
    lane.clock.advance(120)
    with pytest.raises(WorkflowError, match="neither routed .* nor unrouted as recorded"):
        lane.dispatch()
    [record] = lane.dispatch_records()
    assert record["state"] == "pending" and len(lane.runner.slings()) == 1


@pytest.mark.parametrize(
    "stamp,match",
    [
        ("yesterday", "unparsable"),
        (None, "unparsable"),
        ("2030-01-01T12:00:00+02:00", "unparsable"),
        ("2031-01-01T00:00:00.000000Z", "in the future"),
    ],
)
def test_an_unparsable_or_future_last_sling_at_refuses(lane, stamp, match):
    lane.runner.sling_modes = ["timeout"]
    with pytest.raises(WorkflowError, match="timed out"):
        lane.dispatch()

    def change(data):
        for record in data["coordination"].values():
            if record["request"]["action"] == "dispatch":
                if stamp is None:
                    del record["last_sling_at"]
                else:
                    record["last_sling_at"] = stamp

    lane.edit_journal(change)
    lane.clock.advance(120)
    with pytest.raises(WorkflowError, match=match):
        lane.dispatch()
    assert len(lane.runner.slings()) == 1


def test_a_pending_dispatch_refuses_every_other_coordination_but_not_log(lane):
    coordinate(lane.root, "ga-test", "note", {"text": "earlier"}, lane.runner, registry=lane.registry)
    lane.runner.sling_modes = ["timeout"]
    with pytest.raises(WorkflowError, match="timed out"):
        lane.dispatch()
    for action, fields in (
        ("note", {"text": "earlier"}),  # even the replay of a verified note
        ("note", {"text": "new"}),
        ("create", {"title": "t", "description": "d", "acceptance": "a"}),
        ("depend", {"blocker": "ga-other"}),
    ):
        with pytest.raises(WorkflowError, match="pending dispatch refuses"):
            coordinate(lane.root, "ga-test", action, fields, lane.runner, registry=lane.registry)


def test_a_dispatch_for_another_target_waits_for_the_pending_one(tmp_path, monkeypatch):
    lane = make_lane(tmp_path, monkeypatch)
    commit_profile(lane.seat, seat_profile(lane.seat, dispatch_targets=[TARGET, "future-project/b"]))
    lane.runner.agents.append({"qualified_name": "future-project/b", "suspended": False})
    lane.runner.sling_modes = ["timeout"]
    with pytest.raises(WorkflowError, match="timed out"):
        lane.dispatch()
    with pytest.raises(WorkflowError, match="another coordination intent is unresolved"):
        lane.dispatch(target="future-project/b")
    assert len(lane.runner.slings()) == 1


def test_log_pending_id_still_runs_while_a_dispatch_is_pending(lane):
    lane.runner.sling_modes = ["timeout"]
    with pytest.raises(WorkflowError, match="timed out"):
        lane.dispatch()
    result = log(lane.root, None, "Recorded the failed call", lane.runner, pending_id="0123456789ab")
    assert result["status"] == "applied"


def test_reconcile_attachment_refuses_while_a_dispatch_is_pending(lane):
    from workflow_attachment_reconcile import reconcile_attachment
    from workflow_ownership import canonical_json

    lane.runner.sling_modes = ["timeout"]
    with pytest.raises(WorkflowError, match="timed out"):
        lane.dispatch()
    request = {"bead_id": "ga-test", "action": "depend", "fields": {"blocker": "ga-other"}}
    key = hashlib.sha256(canonical_json(request).encode()).hexdigest()

    def pending_depend(data):
        data["coordination"][key] = {
            "state": "pending",
            "request": request,
            "before": {"id": "ga-test"},
            "blocker_before": {"id": "ga-other"},
        }

    lane.edit_journal(pending_depend)
    with pytest.raises(WorkflowError, match="another coordination transaction is unresolved"):
        reconcile_attachment(
            lane.root, key, "0" * 64, "1" * 64, "2" * 64, lane.runner, registry=lane.registry
        )


# --- The bounded runner ----------------------------------------------------------------


def test_the_bounded_runner_returns_output_and_refuses_failure():
    runner = CommandRunner()
    result = runner.run([sys.executable, "-c", "print('ok')"], timeout=30)
    assert result.stdout == "ok\n" and result.returncode == 0
    with pytest.raises(WorkflowError, match="command failed"):
        runner.run([sys.executable, "-c", "raise SystemExit(3)"], timeout=30)


def test_a_timeout_kills_the_whole_process_group(tmp_path):
    marker = tmp_path / "grandchild-survived"
    grandchild = f"import time, pathlib; time.sleep(2); pathlib.Path({str(marker)!r}).write_text('x')"
    parent = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {grandchild!r}]); time.sleep(60)"
    )
    started = time.monotonic()
    with pytest.raises(WorkflowError, match="timed out after 0.5 s"):
        CommandRunner().run([sys.executable, "-c", parent], timeout=0.5)
    assert time.monotonic() - started < 10
    time.sleep(3)
    assert not marker.exists()
