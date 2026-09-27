"""gct-oak5 C1 window: the one rule that picks the next job after RESUME, WATCH-LOOP or any fallback.

Every job's admission is `select(read_state(...)) == its own name`, evaluated on its own fresh records, so the
coordinator's choice and the job's own check can never disagree in a way that runs the wrong job: a job that sees a
different state refuses before any mutation, and the refusal marks it used.

Inputs, and nothing else:
- the window root's lifecycle records (the inherited window-base-r11 names);
- which jobs have a runner done record (used, whatever the exit status);
- whether a rig hold passed (`result.json` with ok true in a hold root);
- the last final observation a watcher recorded (absent or unreadable means "not quiet").
Exit statuses are never read: a used job is used, and the records say what it did.
"""
import json
from pathlib import Path

ACTIONS = ('rig-resume', 'city-resume', 'city-suspend', 'rig-suspend')
ABSENT, COMPLETE, INCOMPLETE, FAILED = 'absent', 'complete', 'incomplete', 'failed'

# The completed-action sequences window-base-r11's permitted order can produce
# (window-base-r11.py:660-663); anything else is stranded.
VALID = {
    (),
    ('rig-resume',),
    ('rig-resume', 'rig-suspend'),
    ('rig-resume', 'city-resume'),
    ('rig-resume', 'city-resume', 'city-suspend'),
    ('rig-resume', 'city-resume', 'city-suspend', 'rig-suspend'),
}

WATCH_LOOP, WATCH_LOOP_2, CONTAIN_2, HOLD_1, HOLD_2 = 'WATCH-LOOP', 'WATCH-LOOP-2', 'CONTAIN-2', 'HOLD-1', 'HOLD-2'
JOBS = (WATCH_LOOP, WATCH_LOOP_2, CONTAIN_2, HOLD_1, HOLD_2)
CLOSE, STOP = 'CLOSE', 'STOP'
WATCHERS = (WATCH_LOOP, WATCH_LOOP_2)
HOLDS = (HOLD_1, HOLD_2)


def completed(lifecycle):
    return tuple(a for a in ACTIONS if lifecycle[a] == COMPLETE)


def quiet(obs):
    """The quiet end: C1 closed, the session Bead closed in a drain-ack end state, an empty census, no orphan
    probe decision. Anything missing reads as not quiet."""
    return bool(obs) and all(obs.get(k) is True for k in ('c1_closed', 'session_drain_ack_closed', 'census_empty')) \
        and obs.get('orphan_decision') is False


def _first_unused(names, used):
    for name in names:
        if name not in used:
            return name
    return None


def _hold(used):
    return _first_unused(HOLDS, used) or STOP


def select(lifecycle, used, hold_passed, obs):
    """Return the next job, CLOSE, or STOP (a standing stop: the operator is told)."""
    assert set(lifecycle) == set(ACTIONS) and set(used) <= set(JOBS)
    if hold_passed:
        # The inherited CLOSE admits a passing hold (close-r11.py:103-105) and tears down.
        return CLOSE
    if any(lifecycle[a] in (INCOMPLETE, FAILED) for a in ACTIONS):
        return _hold(used)
    seq = completed(lifecycle)
    if seq not in VALID:
        return _hold(used)
    if seq == () or lifecycle['rig-suspend'] == COMPLETE:
        # Never resumed, or scheduling held by a completed rig suspend: CLOSE's own held predicate.
        return CLOSE
    # The rig is resumed and not suspended.
    city_live = seq == ('rig-resume', 'city-resume')
    if not city_live or quiet(obs):
        # No worker can be live (city never resumed or already suspended) or the quiet end: contain by events.
        return CONTAIN_2 if CONTAIN_2 not in used else _hold(used)
    # A worker may be live: watch it (the watcher contains on any trigger), else hold.
    return _first_unused(WATCHERS, used) or _hold(used)


def contain_steps(lifecycle):
    """CONTAIN-2 acts by events, like the inherited CONTAIN-1 (operator/CONTAIN-1.sh:40-45)."""
    steps = []
    if lifecycle['city-resume'] == COMPLETE and lifecycle['city-suspend'] == ABSENT:
        steps.append('city-suspend')
    if lifecycle['rig-resume'] == COMPLETE and lifecycle['rig-suspend'] == ABSENT:
        steps.append('rig-suspend')
    return steps


def close_held(lifecycle, hold_passed):
    """close-r11.py:95-105: a rig-suspend event, a never-resumed window, or a passing hold."""
    return hold_passed or lifecycle['rig-suspend'] == COMPLETE or completed(lifecycle) == () and all(
        lifecycle[a] == ABSENT for a in ACTIONS)


# ---- reading the state from disk (no gc, bd or git call) ----

def _exists(root, name):
    return (root/name).exists()


def action_state(root, action):
    intent = _exists(root, 'suspension-%s-intent.json' % action)
    event = _exists(root, 'suspension-%s-event.json' % action)
    started = _exists(root, '%s-started.json' % action)
    phase = _exists(root, '%s-phase.json' % action)
    if _exists(root, 'suspension-%s-failure.json' % action) or _exists(root, 'suspension-%s-refused-after.json' % action):
        return FAILED
    if not (intent or event or started or phase):
        return ABSENT
    if intent and event and started and phase:
        return COMPLETE
    return INCOMPLETE


def stray_phases(root):
    """A started phase without its phase record, for any name (window-base-r11 complete_containment)."""
    starts = {p.name[:-len('-started.json')] for p in root.glob('*-started.json')}
    ends = {p.name[:-len('-phase.json')] for p in root.glob('*-phase.json')}
    return sorted(starts - ends)


def read_state(window, done, wrapper_prefix, hold_roots, obs_path):
    window, done = Path(window), Path(done)
    lifecycle = {a: action_state(window, a) for a in ACTIONS}
    if stray_phases(window):
        # Mark the first non-failed action incomplete so select() holds.
        for a in ACTIONS:
            if lifecycle[a] != FAILED:
                lifecycle[a] = INCOMPLETE
                break
    used = set()
    for record in sorted(done.glob('*.json')) if done.is_dir() else []:
        try:
            value = json.loads(record.read_text())
            wrapper = str(value['job']['wrapper'])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        for job in JOBS:
            if wrapper == wrapper_prefix + job + '.sh':
                used.add(job)
    hold_passed = False
    for result in sorted(Path(p) for p in hold_roots):
        try:
            hold_passed = hold_passed or json.loads((result/'result.json').read_text()).get('ok') is True
        except (OSError, ValueError, AttributeError):
            continue
    try:
        obs = json.loads(Path(obs_path).read_text()) if obs_path else None
        obs = obs if isinstance(obs, dict) else None
    except (OSError, ValueError):
        obs = None
    return dict(lifecycle=lifecycle, used=used, hold_passed=hold_passed, obs=obs)
