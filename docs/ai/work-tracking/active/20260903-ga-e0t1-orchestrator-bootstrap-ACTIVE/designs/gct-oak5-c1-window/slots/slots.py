"""gct-oak5 C1 window: the one rule that picks the next job after RESUME, WATCH-LOOP or any fallback.

Every job's admission is `select(**read_state(..., own_job_id=<its runner job id>)) == its own name`, evaluated on
its own fresh records, so a job that sees a different state than the coordinator refuses before any mutation, and
the refusal marks it used.

Inputs, and nothing else:
- the window root's lifecycle records (the inherited window-base-r11 names);
- which jobs the runner started (a started record, finished or not, is a used job), except the caller's own run;
- whether a hold of this window passed (`result.json` naming this window with ok true);
- the newest final observation a watcher of this window recorded (absent or unreadable means "not quiet").
Exit statuses are never read. Anything unreadable in the runner's done directory is `broken`, which stops.
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

# The runner's done directory (gct-jobrunner/jobrunner.py:426, 438, 451, 274): started, final, refused (never
# launched), resolved, and the coordinator's cleared halt files.
IGNORED_SUFFIXES = ('.resolved.json', '.halted-cleared.json')


def completed(lifecycle):
    return tuple(a for a in ACTIONS if lifecycle[a] == COMPLETE)


def quiet(obs):
    """The quiet end: C1 closed, the session Bead closed in a drain-ack end state, an empty census, no orphan
    probe decision. Anything missing reads as not quiet."""
    return isinstance(obs, dict) and all(
        obs.get(k) is True for k in ('c1_closed', 'session_drain_ack_closed', 'census_empty')) \
        and obs.get('orphan_decision') is False


def _first_unused(names, used):
    for name in names:
        if name not in used:
            return name
    return None


def _hold(used):
    return _first_unused(HOLDS, used) or STOP


def select(lifecycle, used, hold_passed, obs, stranded=False, broken=False):
    """Return the next job, CLOSE, or STOP (a standing stop: the operator is told)."""
    if not (isinstance(lifecycle, dict) and set(lifecycle) == set(ACTIONS)
            and all(v in (ABSENT, COMPLETE, INCOMPLETE, FAILED) for v in lifecycle.values())
            and set(used) <= set(JOBS)):
        raise ValueError('select: malformed state')
    if broken:
        return STOP
    if hold_passed:
        # The inherited CLOSE admits a passing hold (close-r11.py:103-105) and tears down.
        return CLOSE
    if stranded or any(lifecycle[a] in (INCOMPLETE, FAILED) for a in ACTIONS):
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
        # The city was never resumed (partial RESUME), is already suspended (a running lane row may remain; the
        # rig suspend and CLOSE's drain handle it), or the run reached the quiet end: contain by events.
        return CONTAIN_2 if CONTAIN_2 not in used else _hold(used)
    # The city is resumed and a worker may be live: watch it (the watcher contains on any trigger), else hold.
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
    return hold_passed or lifecycle['rig-suspend'] == COMPLETE or all(lifecycle[a] == ABSENT for a in ACTIONS)


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
    """A started phase without its phase record, or a phase record without its start, for any name
    (window-base-r11 complete_containment refuses on either)."""
    starts = {p.name[:-len('-started.json')] for p in root.glob('*-started.json')}
    ends = {p.name[:-len('-phase.json')] for p in root.glob('*-phase.json')}
    return sorted(starts ^ ends)


def _load(path):
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise ValueError('not an object')
    return value


def _wrapper(value):
    wrapper = value['job']['wrapper']
    if not isinstance(wrapper, str):
        raise ValueError('wrapper')
    return wrapper


def read_used(done, wrapper_prefix, own_job_id=None):
    """Return (used jobs, broken). A job is used once the runner wrote its started record."""
    done = Path(done)
    if not wrapper_prefix.endswith('/operator/') or not done.is_dir():
        return set(), True
    used, started, final = set(), set(), set()
    try:
        for entry in sorted(done.iterdir()):
            name = entry.name
            if name.endswith(IGNORED_SUFFIXES) or '.refused-' in name:
                continue
            if name.endswith('.started.json'):
                job_id, kind = name[:-len('.started.json')], started
            elif name.endswith('.json') and name.count('.') == 1:
                job_id, kind = name[:-len('.json')], final
            else:
                return set(), True
            wrapper = _wrapper(_load(entry))
            kind.add(job_id)
            if job_id == own_job_id and kind is started:
                continue
            for job in JOBS:
                if wrapper == wrapper_prefix + job + '.sh':
                    used.add(job)
    except (OSError, ValueError, KeyError, TypeError):
        return set(), True
    if own_job_id is not None and (own_job_id not in started or own_job_id in final):
        return set(), True
    return used, False


def read_state(window, done, wrapper_prefix, hold_roots, watcher_roots, own_job_id=None):
    window = Path(window)
    lifecycle = {a: action_state(window, a) for a in ACTIONS}
    used, broken = read_used(done, wrapper_prefix, own_job_id)
    hold_passed = False
    for root in hold_roots:
        try:
            result = _load(Path(root)/'result.json')
        except (OSError, ValueError):
            continue
        hold_passed = hold_passed or (result.get('ok') is True and result.get('window') == str(window))
    obs, newest = None, -1
    for root in watcher_roots:
        try:
            value = _load(Path(root)/'final-observation.json')
        except (OSError, ValueError):
            continue
        written = value.get('written_ns')
        if value.get('window') == str(window) and isinstance(written, int) and written > newest:
            obs, newest = value, written
    return dict(lifecycle=lifecycle, used=used, hold_passed=hold_passed, obs=obs,
                stranded=bool(stray_phases(window)), broken=broken)
