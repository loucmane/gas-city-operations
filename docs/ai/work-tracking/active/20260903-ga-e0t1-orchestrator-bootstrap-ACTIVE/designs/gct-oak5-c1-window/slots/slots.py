"""gct-oak5 C1 window: the one rule that picks the next job after RESUME, WATCH-LOOP or any fallback.

Every job's admission is `select(**read_state(..., own_job_id=<its runner job id>)) == its own name`, evaluated on
its own fresh records, so a job that sees a different state than the coordinator refuses before any mutation, and
the refusal marks it used.

Inputs, and nothing else:
- the window root's lifecycle records (the inherited window-base-r11 names);
- which jobs the runner started at this package commit (a started record, finished or not, is a used job), except
  the caller's own run, whose record must name its own wrapper and this commit;
- whether a hold of this window passed (`result.json` naming this window with ok true);
- the newest final observation a watcher of this window recorded (absent or unreadable means "not quiet").
Exit statuses are never read. Anything unreadable in the runner's done directory is `broken`: a hold, never a job
that could act on a live worker.
"""
import json
import os
import re
import stat
from pathlib import Path

# The runner records `job.wrapper` exactly as queued, relative to the repository (gct-jobrunner/jobrunner.py:69-71,
# 311, 437-438); only `argv` carries the absolute path.
RUNNER_PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/'
WRAPPER_PREFIX = RUNNER_PREFIX + 'gct-oak5-c1-window/operator/'
RECORD_LIMIT = 1024 * 1024  # jobrunner.py RECORD_LIMIT
HEX40 = re.compile(r'[0-9a-f]{40}')  # jobrunner.py HEX40
JOB_ID = re.compile(r'[a-z0-9][a-z0-9-]{0,47}')  # jobrunner.py JOB_ID
# The runner's own unit sits here, and so does every job unit it launches (jobrunner.py:67, 338).
UNIT_PARENT = '0::/user.slice/user-1000.slice/user@1000.service/app.slice/'

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
    probe decision and no containment reason. Anything missing reads as not quiet."""
    return isinstance(obs, dict) and all(
        obs.get(k) is True for k in ('c1_closed', 'session_drain_ack_closed', 'census_empty')) \
        and obs.get('orphan_decision') is False and 'contained_reason' in obs and obs['contained_reason'] is None


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
    if hold_passed:
        # The inherited CLOSE admits a passing hold (close-r11.py:103-105) and tears down.
        return CLOSE
    if broken:
        # The runner's records cannot be read, so `used` is unknown: only a hold, which only suspends, may act.
        # HOLD-1 is the broken-state hold, admitted even when its own record is what is broken. If the runner has
        # already run it, the runner refuses the repeat and the coordinator stops: one hold fewer than the readable
        # path, a stated stop with the operator told.
        return HOLD_1
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
    """close-r11.py:95-105: a rig-suspend event, a never-resumed window, or a passing hold. The never-resumed branch
    also needs STAGE's `stage-pass.json` (close-r11.py:100-102), which RESUME requires before select() ever runs."""
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
    """Read like the runner's read_owned (jobrunner.py:157-171): no links, a regular single-link file owned by the
    caller, at most RECORD_LIMIT bytes."""
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 \
                or info.st_size > RECORD_LIMIT:
            raise ValueError('not a small regular owned file: %s' % path)
        chunks = []
        while chunk := os.read(fd, 1 << 20):
            chunks.append(chunk)
    finally:
        os.close(fd)
    raw = b''.join(chunks)
    if len(raw) > RECORD_LIMIT:
        raise ValueError('record grew past the limit')

    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError('duplicate key %r' % key)  # jobrunner.py strict_json
            seen[key] = value
        return seen
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
    except RecursionError:
        raise ValueError('record nested too deeply')
    if not isinstance(value, dict):
        raise ValueError('not an object')
    return value


def _job(value):
    job = value['job']
    if not (isinstance(job, dict) and isinstance(job.get('wrapper'), str) and isinstance(job.get('commit'), str)):
        raise ValueError('job')
    return job['wrapper'], job['commit']


def read_used(done, commit, own_job=None, own_job_id=None):
    """Return (used jobs, broken). A job is used once the runner wrote its started record at this commit."""
    done = Path(done)
    try:
        info = os.lstat(done)
    except OSError:
        return set(), True
    if (own_job is None) != (own_job_id is None) or own_job not in (None,) + JOBS \
            or not (stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()) \
            or not (isinstance(commit, str) and HEX40.fullmatch(commit)):
        return set(), True
    used, started, final, own = set(), set(), set(), None
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
            wrapper, job_commit = _job(_load(entry))
            kind.add(job_id)
            if job_id == own_job_id and kind is started:
                own = (wrapper, job_commit)
                continue
            if job_commit != commit:
                continue
            for job in JOBS:
                if wrapper == WRAPPER_PREFIX + job + '.sh':
                    used.add(job)
    except (OSError, ValueError, KeyError, TypeError):
        return set(), True
    if own_job_id is not None and (own_job_id in final or own != (WRAPPER_PREFIX + own_job + '.sh', commit)):
        return set(), True
    return used, False


def own_job_id_from_cgroup(text):
    """The runner launches every job as the unit gc-job-<id>.service (jobrunner.py:338)."""
    lines = [line for line in text.splitlines() if line.startswith('0::')]
    if len(lines) != 1 or not lines[0].startswith(UNIT_PARENT):
        raise ValueError('cgroup')
    leaf = lines[0][len(UNIT_PARENT):]
    if not (leaf.startswith('gc-job-') and leaf.endswith('.service')):
        raise ValueError('not a runner job unit')
    job_id = leaf[len('gc-job-'):-len('.service')]
    if not JOB_ID.fullmatch(job_id):
        raise ValueError('job id')
    return job_id


def read_state(window, done, commit, hold_roots, watcher_roots, boot_id, own_job=None, own_job_id=None):
    window = Path(window)
    lifecycle = {a: action_state(window, a) for a in ACTIONS}
    used, broken = read_used(done, commit, own_job, own_job_id)
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
        # CLOCK_BOOTTIME restarts at boot, so only this boot's observations are ordered.
        if value.get('window') == str(window) and value.get('boot_id') == boot_id and isinstance(written, int) \
                and written > newest:
            obs, newest = value, written
    return dict(lifecycle=lifecycle, used=used, hold_passed=hold_passed, obs=obs,
                stranded=bool(stray_phases(window)), broken=broken)
