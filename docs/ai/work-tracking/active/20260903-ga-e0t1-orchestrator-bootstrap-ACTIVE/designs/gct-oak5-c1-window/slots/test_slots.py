import itertools
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slots as S  # noqa: E402

A = S.ACTIONS
PERMITTED = {(): ['rig-resume'], ('rig-resume',): ['city-resume', 'rig-suspend'],
             ('rig-resume', 'city-resume'): ['city-suspend'],
             ('rig-resume', 'city-resume', 'city-suspend'): ['rig-suspend']}
QUIET = dict(c1_closed=True, session_drain_ack_closed=True, census_empty=True, orphan_decision=False,
             contained_reason=None)
LIVE = dict(c1_closed=False, session_drain_ack_closed=False, census_empty=False, orphan_decision=False,
            contained_reason=None)
OBS = (None, QUIET, LIVE, dict(QUIET, orphan_decision=True), dict(QUIET, census_empty=False),
       dict(QUIET, contained_reason='trigger'))
BOOT = 'b' * 36


def lc(**kw):
    d = {a: S.ABSENT for a in A}
    d.update({k.replace('_', '-'): v for k, v in kw.items()})
    return d


def all_states():
    for vals in itertools.product((S.ABSENT, S.COMPLETE, S.INCOMPLETE, S.FAILED), repeat=4):
        life = dict(zip(A, vals))
        for n in range(len(S.JOBS) + 1):
            for used in itertools.combinations(S.JOBS, n):
                for hold in (False, True):
                    for obs in OBS:
                        for flags in ({}, dict(stranded=True), dict(broken=True)):
                            yield life, set(used), hold, obs, flags


def test_total_and_never_a_used_job():
    for life, used, hold, obs, flags in all_states():
        r = S.select(life, used, hold, obs, **flags)
        assert r in S.JOBS + (S.CLOSE, S.STOP)
        if flags.get('broken') and not hold:
            assert r == S.HOLD_1          # used is unknown when broken; read_state then passes an empty set
        else:
            assert r not in used


def test_close_only_when_close_is_held():
    for life, used, hold, obs, flags in all_states():
        if S.select(life, used, hold, obs, **flags) == S.CLOSE:
            assert S.close_held(life, hold), (life, used, hold, obs, flags)


def test_stop_only_after_both_holds_used():
    for life, used, hold, obs, flags in all_states():
        if S.select(life, used, hold, obs, **flags) == S.STOP:
            assert set(S.HOLDS) <= used and not hold and not flags.get('broken')


def test_stranded_goes_to_a_hold():
    for life, used, hold, obs, flags in all_states():
        if hold:
            continue
        seq = S.completed(life)
        if flags or any(v in (S.INCOMPLETE, S.FAILED) for v in life.values()) or seq not in S.VALID:
            assert S.select(life, used, hold, obs, **flags) in S.HOLDS + (S.STOP,)


def test_possibly_live_worker_is_watched_or_held():
    live = lc(rig_resume=S.COMPLETE, city_resume=S.COMPLETE)
    for n in range(len(S.JOBS) + 1):
        for used in itertools.combinations(S.JOBS, n):
            for obs in OBS:
                r = S.select(live, set(used), False, obs)
                if S.quiet(obs):
                    assert r in (S.CONTAIN_2,) + S.HOLDS + (S.STOP,)
                else:
                    assert r in S.WATCHERS + S.HOLDS + (S.STOP,)
    # City suspended, rig not: a lane row may still run; the rig suspend (CONTAIN-2) or a hold, never CLOSE.
    between = lc(rig_resume=S.COMPLETE, city_resume=S.COMPLETE, city_suspend=S.COMPLETE)
    for n in range(len(S.JOBS) + 1):
        for used in itertools.combinations(S.JOBS, n):
            for obs in OBS:
                assert S.select(between, set(used), False, obs) in (S.CONTAIN_2,) + S.HOLDS + (S.STOP,)


def test_named_states():
    assert S.select(lc(), set(), False, None) == S.CLOSE                                   # RESUME refused first
    assert S.select(lc(rig_resume=S.COMPLETE), set(), False, None) == S.CONTAIN_2          # partial RESUME
    assert S.contain_steps(lc(rig_resume=S.COMPLETE)) == ['rig-suspend']
    live = lc(rig_resume=S.COMPLETE, city_resume=S.COMPLETE)
    assert S.select(live, set(), False, None) == S.WATCH_LOOP
    assert S.select(live, {S.WATCH_LOOP}, False, None) == S.WATCH_LOOP_2                  # WATCH-LOOP died
    assert S.select(live, {S.WATCH_LOOP}, False, QUIET) == S.CONTAIN_2                    # died at the quiet end
    assert S.select(live, {S.WATCH_LOOP, S.WATCH_LOOP_2}, False, LIVE) == S.HOLD_1
    between = lc(rig_resume=S.COMPLETE, city_resume=S.COMPLETE, city_suspend=S.COMPLETE)
    assert S.select(between, {S.WATCH_LOOP}, False, None) == S.CONTAIN_2                 # killed between the pair
    assert S.contain_steps(between) == ['rig-suspend']
    assert S.select(between, {S.WATCH_LOOP, S.CONTAIN_2}, False, None) == S.HOLD_1        # CONTAIN-2 refused
    done = dict(between, **{'rig-suspend': S.COMPLETE})
    assert S.select(done, {S.WATCH_LOOP}, False, None) == S.CLOSE
    assert S.select(lc(rig_resume=S.COMPLETE, rig_suspend=S.COMPLETE), set(), False, None) == S.CLOSE
    bad = dict(live, **{'city-resume': S.FAILED})
    assert S.select(bad, set(), False, None) == S.HOLD_1
    assert S.select(bad, {S.HOLD_1}, False, None) == S.HOLD_2
    assert S.select(bad, {S.HOLD_1, S.HOLD_2}, False, None) == S.STOP
    assert S.select(bad, {S.HOLD_1}, True, None) == S.CLOSE                              # hold passed: CLOSE tears down


# ---- a model of every job's possible effects, driven to the end ----

def attempt(life, action):
    """window-base-r11 lifecycle(): refuses before the intent (no record) unless nothing failed, the action's
    outputs are absent and the order permits it; otherwise the command completes, fails, or is killed."""
    assert life[action] == S.ABSENT, 'a job asked to repeat ' + action
    seq = S.completed(life)
    if any(v == S.FAILED for v in life.values()) or action not in PERMITTED.get(seq, []):
        return [None]
    # A permitted step can still refuse before its intent (digests, active_epoch, the chain: window-base-r11.py:644-665).
    return [None] + [dict(life, **{action: o}) for o in (S.COMPLETE, S.FAILED, S.INCOMPLETE)]


def run_steps(life, steps):
    """Run steps in order, stopping at the first that does not complete; every branch."""
    if not steps:
        return [life]
    out = []
    for nxt in attempt(life, steps[0]):
        if nxt is None:
            out.append(life)
        elif nxt[steps[0]] == S.COMPLETE:
            out += run_steps(nxt, steps[1:])
        else:
            out.append(nxt)
    return out


def effects(job, life):
    if job in S.HOLDS:
        return [(life, False), (life, True)]
    if job == S.CONTAIN_2:
        return [(x, False) for x in run_steps(life, S.contain_steps(life))] + [(life, False)]
    # A watcher dies with no action, or runs the containment pair once (in-process flag), with every outcome.
    return [(life, False)] + [(x, False) for x in run_steps(life, S.contain_steps(life))]


def resume_outcomes():
    # RESUME: rig-resume, the queue audit (which can refuse: modelled by city-resume's None branch), city-resume.
    out = run_steps(lc(), ['rig-resume', 'city-resume'])
    assert lc() in out and lc(rig_resume=S.COMPLETE) in out
    return out


def test_every_run_ends_at_close_or_stop_and_repeats_nothing():
    visited, ends = set(), set()
    frontier = [(life, frozenset(), False) for life in resume_outcomes()]
    while frontier:
        life, used, hold = frontier.pop()
        key = (tuple(sorted(life.items())), used, hold)
        if key in visited:
            continue
        visited.add(key)
        assert len(used) <= len(S.JOBS)
        for obs in OBS:
            r = S.select(life, set(used), hold, obs)
            if r in (S.CLOSE, S.STOP):
                if r == S.CLOSE:
                    assert S.close_held(life, hold)
                ends.add(r)
                continue
            # The job's own admission re-reads the state; a changed observation makes it refuse (used, no effect).
            frontier.append((life, used | {r}, hold))
            for nxt, passed in effects(r, life):
                frontier.append((nxt, used | {r}, hold or passed))
    assert ends == {S.CLOSE, S.STOP} and len(visited) > 50
    between = lc(rig_resume=S.COMPLETE, city_resume=S.COMPLETE, city_suspend=S.COMPLETE)
    assert any(dict(k[0]) == between for k in visited)


# ---- reading records from disk ----

def touch(root, *names):
    for n in names:
        (root/n).write_text('{}')


def full(action):
    return ('suspension-%s-intent.json' % action, 'suspension-%s-event.json' % action,
            '%s-started.json' % action, '%s-phase.json' % action)


COMMIT = 'c' * 40
RUNNER = Path(__file__).resolve().parents[2]/'gct-jobrunner'/'jobrunner.py'


def runner(done, job_id, job, final=True, exit_code=0, commit=COMMIT, wrapper=None):
    """The runner's record shape, keys as in a real pair (done/ga-nibd-s2r2-watch-1.started.json and .json):
    started has admitted, argv, job, job_file, received, started; job has commit, job_id, reviews, wrapper,
    wrapper_sha256 with the wrapper RELATIVE to the repository; the final record adds ended, exit, stderr, stdout,
    unit_state_after."""
    wrapper = wrapper or S.WRAPPER_PREFIX + job + '.sh'
    record = dict(admitted=True, argv=['/usr/bin/systemd-run', '--unit=gc-job-' + job_id, '/abs/' + wrapper, commit],
                  job=dict(commit=commit, job_id=job_id, reviews=[], wrapper=wrapper, wrapper_sha256='0' * 64),
                  job_file=job_id + '.json', received='r', started='s')
    (done/(job_id + '.started.json')).write_text(json.dumps(record))
    if final:
        (done/(job_id + '.json')).write_text(json.dumps(dict(record, ended='e', exit=exit_code, stderr='', stdout='',
                                                              unit_state_after='inactive')))
        (done/(job_id + '.halted-cleared.json')).write_text('job finished, not json')


def test_wrapper_prefix_is_the_runner_relative_form():
    import importlib.util
    spec = importlib.util.spec_from_file_location('jobrunner_under_test', RUNNER)
    runner_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner_module)          # guarded by __main__, so importing runs nothing
    assert S.RUNNER_PREFIX == runner_module.PREFIX
    assert S.RECORD_LIMIT == runner_module.RECORD_LIMIT
    assert S.HEX40.pattern == runner_module.HEX40.pattern and S.JOB_ID.pattern == runner_module.JOB_ID.pattern
    for job in S.JOBS:
        assert runner_module.WRAPPER.fullmatch(S.WRAPPER_PREFIX + job + '.sh')
    assert not S.WRAPPER_PREFIX.startswith('/')


def test_read_state(tmp_path):
    w, d = tmp_path/'w', tmp_path/'done'
    w.mkdir(), d.mkdir()
    touch(w, *full('rig-resume'), *full('city-resume'), 'suspension-city-suspend-intent.json')
    runner(d, 'oak5-c1-watch', S.WATCH_LOOP, exit_code=137)
    runner(d, 'old-attempt', S.WATCH_LOOP_2, commit='d' * 40)                    # another commit: not this package
    runner(d, 'other-window', S.WATCH_LOOP_2, wrapper='docs/ai/x/designs/gct-e8ex-window/operator/WATCH-1.sh')
    (d/'x.refused-1.json').write_text('{}')
    h = tmp_path/'hold'
    h.mkdir()
    (h/'result.json').write_text(json.dumps(dict(ok=True, window='/elsewhere')))
    o1, o2 = tmp_path/'o1', tmp_path/'o2'
    o1.mkdir(), o2.mkdir()
    (o1/'final-observation.json').write_text(json.dumps(dict(QUIET, window=str(w), written_ns=2, boot_id=BOOT)))
    (o2/'final-observation.json').write_text(json.dumps(dict(LIVE, window=str(w), written_ns=1, boot_id=BOOT)))
    st = S.read_state(w, d, COMMIT, [h], [o2, o1], BOOT)
    assert st['lifecycle'] == lc(rig_resume=S.COMPLETE, city_resume=S.COMPLETE, city_suspend=S.INCOMPLETE)
    assert st['used'] == {S.WATCH_LOOP} and st['hold_passed'] is False and S.quiet(st['obs'])
    assert not st['broken'] and not st['stranded']
    assert S.select(**st) == S.HOLD_1


def test_each_job_passes_its_own_admission_with_the_runner_layout(tmp_path):
    """The runner writes <id>.started.json before launching (jobrunner.py:438); the caller excludes its own."""
    w = tmp_path/'w'
    w.mkdir()
    touch(w, *full('rig-resume'), *full('city-resume'))
    d = tmp_path/'done'
    d.mkdir()
    for n, job in enumerate([S.WATCH_LOOP, S.WATCH_LOOP_2, S.HOLD_1, S.HOLD_2]):
        runner(d, 'job%d' % n, job, final=False)
        st = S.read_state(w, d, COMMIT, [], [], BOOT, own_job=job, own_job_id='job%d' % n)
        assert not st['broken'] and S.select(**st) == job, job
        coordinator = S.read_state(w, d, COMMIT, [], [], BOOT)
        assert job in coordinator['used']                      # started, unfinished: used for everyone else
        (d/('job%d.json' % n)).write_text((d/('job%d.started.json' % n)).read_text())
    w2 = tmp_path/'w2'
    w2.mkdir()
    touch(w2, *full('rig-resume'))
    d2 = tmp_path/'done2'
    d2.mkdir()
    runner(d2, 'c2', S.CONTAIN_2, final=False)
    assert S.select(**S.read_state(w2, d2, COMMIT, [], [], BOOT, own_job=S.CONTAIN_2, own_job_id='c2')) == S.CONTAIN_2


def test_own_record_must_name_its_own_wrapper_and_commit(tmp_path):
    w = tmp_path/'w'
    w.mkdir()
    d = tmp_path/'done'
    d.mkdir()
    runner(d, 'a', S.WATCH_LOOP_2, final=False)
    assert S.read_state(w, d, COMMIT, [], [], BOOT, own_job=S.HOLD_1, own_job_id='a')['broken']       # another job's run
    assert S.read_state(w, d, 'e' * 40, [], [], BOOT, own_job=S.WATCH_LOOP_2, own_job_id='a')['broken']  # another commit
    runner(d, 'b', S.WATCH_LOOP, final=False, wrapper='/abs/' + S.WRAPPER_PREFIX + 'WATCH-LOOP.sh')
    assert S.read_state(w, d, COMMIT, [], [], BOOT, own_job=S.WATCH_LOOP, own_job_id='b')['broken']   # absolute form
    assert S.read_state(w, d, COMMIT, [], [], BOOT, own_job_id='a')['broken']                         # job id without name


def test_broken_inputs_hold(tmp_path):
    w = tmp_path/'w'
    w.mkdir()
    touch(w, *full('rig-resume'), *full('city-resume'))
    d = tmp_path/'done'
    assert S.read_state(w, d, COMMIT, [], [], BOOT)['broken']                          # no done directory
    d.mkdir()
    (d/'bad.json').write_text('not json')
    st = S.read_state(w, d, COMMIT, [], [], BOOT)
    assert st['broken'] and S.select(**st) == S.HOLD_1                         # only a hold may act
    (d/'bad.json').unlink()
    (d/'odd.name.json').write_text('{}')
    assert S.read_state(w, d, COMMIT, [], [], BOOT)['broken']                          # unknown record shape
    (d/'odd.name.json').unlink()
    (d/'big.json').write_text(json.dumps(dict(job=dict(wrapper='w', commit=COMMIT), pad='x' * S.RECORD_LIMIT)))
    assert S.read_state(w, d, COMMIT, [], [], BOOT)['broken']                          # over the size limit
    (d/'big.json').unlink()
    (tmp_path/'target.json').write_text(json.dumps(dict(job=dict(wrapper='w', commit=COMMIT))))
    (d/'link.json').symlink_to(tmp_path/'target.json')
    assert S.read_state(w, d, COMMIT, [], [], BOOT)['broken']                          # a link
    (d/'link.json').unlink()
    runner(d, 'j', S.WATCH_LOOP)
    assert S.read_state(w, d, COMMIT, [], [], BOOT, own_job=S.WATCH_LOOP, own_job_id='j')['broken']        # already final
    assert S.read_state(w, d, COMMIT, [], [], BOOT, own_job=S.WATCH_LOOP, own_job_id='missing')['broken']  # never started
    held = S.read_state(w, tmp_path/'none', COMMIT, [], [], BOOT)
    assert held['broken'] and S.select(**dict(held, hold_passed=True)) == S.CLOSE      # a passing hold still wins


def test_hold_result_links_are_refused(tmp_path):
    w = tmp_path/'w'
    w.mkdir()
    d = tmp_path/'done'
    d.mkdir()
    real, h = tmp_path/'real', tmp_path/'h'
    real.mkdir(), h.mkdir()
    (real/'result.json').write_text(json.dumps(dict(ok=True, window=str(w))))
    (h/'result.json').symlink_to(real/'result.json')
    assert not S.read_state(w, d, COMMIT, [h], [], BOOT)['hold_passed']
    assert S.read_state(w, d, COMMIT, [real], [], BOOT)['hold_passed']


def test_own_job_id_from_cgroup():
    import pytest
    text = '0::/user.slice/user-1000.slice/user@1000.service/app.slice/gc-job-oak5-c1-hold-1.service\n'
    assert S.own_job_id_from_cgroup(text) == 'oak5-c1-hold-1'
    for bad in ('0::/user.slice/x.scope\n', '', text + text,
                '0::/other.slice/gc-job-a.service\n',
                '0::/user.slice/user-1000.slice/user@1000.service/app.slice/x/gc-job-a.service\n',
                '0::/user.slice/user-1000.slice/user@1000.service/app.slice/gc-job-A_B.service\n'):
        with pytest.raises(ValueError):
            S.own_job_id_from_cgroup(bad)


def test_strict_records_and_commit_format(tmp_path):
    w = tmp_path/'w'
    w.mkdir()
    d = tmp_path/'done'
    d.mkdir()
    assert S.read_state(w, d, 'C' * 40, [], [], BOOT)['broken']                   # not lowercase hex
    assert S.read_state(w, d, 'abc', [], [], BOOT)['broken']
    (d/'dup.json').write_text('{"job": {"wrapper": "w", "commit": "c"}, "job": {}}')
    assert S.read_state(w, d, COMMIT, [], [], BOOT)['broken']                     # duplicate key
    (d/'dup.json').unlink()
    (d/'deep.json').write_text('[' * 200000 + ']' * 200000)
    assert S.read_state(w, d, COMMIT, [], [], BOOT)['broken']                     # nested too deeply
    (d/'deep.json').unlink()
    real = tmp_path/'real-done'
    real.mkdir()
    link = tmp_path/'link-done'
    link.symlink_to(real)
    assert S.read_state(w, link, COMMIT, [], [], BOOT)['broken']                  # a linked done directory


def test_observation_links_other_boots_and_triggers(tmp_path):
    w = tmp_path/'w'
    w.mkdir()
    touch(w, *full('rig-resume'), *full('city-resume'))
    d = tmp_path/'done'
    d.mkdir()
    runner(d, 'wl', S.WATCH_LOOP)
    real, o = tmp_path/'real', tmp_path/'o'
    real.mkdir(), o.mkdir()
    (real/'final-observation.json').write_text(json.dumps(dict(QUIET, window=str(w), written_ns=5, boot_id=BOOT)))
    (o/'final-observation.json').symlink_to(real/'final-observation.json')
    assert S.read_state(w, d, COMMIT, [], [o], BOOT)['obs'] is None               # a link is refused
    assert S.quiet(S.read_state(w, d, COMMIT, [], [real], BOOT)['obs'])
    assert S.read_state(w, d, COMMIT, [], [real], 'x' * 36)['obs'] is None       # another boot
    (real/'final-observation.json').unlink()
    (real/'final-observation.json').write_text(json.dumps(dict(QUIET, window=str(w), written_ns=5, boot_id=BOOT,
                                                             contained_reason='census')))
    st = S.read_state(w, d, COMMIT, [], [real], BOOT)
    assert not S.quiet(st['obs']) and S.select(**st) == S.WATCH_LOOP_2           # a trigger is never the quiet end


def test_select_rejects_malformed_state():
    import pytest
    with pytest.raises(ValueError):
        S.select({'rig-resume': S.ABSENT}, set(), False, None)
    with pytest.raises(ValueError):
        S.select(lc(), {'CLOSE'}, False, None)


def test_read_state_failure_and_stray_phases(tmp_path):
    w = tmp_path/'w'
    w.mkdir()
    d = tmp_path/'done'
    d.mkdir()
    touch(w, *full('rig-resume'), 'city-resume-started.json')
    st = S.read_state(w, d, COMMIT, [], [tmp_path/'missing'], BOOT)
    assert st['obs'] is None and st['used'] == set() and st['stranded']
    assert S.select(**st) == S.HOLD_1
    w2 = tmp_path/'w2'
    w2.mkdir()
    touch(w2, *full('rig-resume'), 'other-phase.json')                          # a phase without its start
    assert S.read_state(w2, d, COMMIT, [], [], BOOT)['stranded']
    touch(w, 'suspension-city-resume-refused-after.json')
    assert S.read_state(w, d, COMMIT, [], [], BOOT)['lifecycle']['city-resume'] == S.FAILED


# CLOSE is a terminal selection, but still proves its own runner identity before acting.
@pytest.mark.parametrize('held_by', ['never-resumed', 'rig-suspend', 'passing-hold'])
def test_close_passes_its_own_admission_with_the_runner_layout(tmp_path, held_by):
    w, d, h = tmp_path/'w', tmp_path/'done', tmp_path/'hold'
    w.mkdir(), d.mkdir(), h.mkdir()
    if held_by == 'rig-suspend':
        touch(w, *full('rig-resume'), *full('rig-suspend'))
    elif held_by == 'passing-hold':
        touch(w, *full('rig-resume'), *full('city-resume'), 'city-suspend-started.json')
        (h/'result.json').write_text(json.dumps(dict(ok=True, window=str(w))))
    coordinator = S.read_state(w, d, COMMIT, [h], [], BOOT)
    assert not coordinator['broken'] and S.select(**coordinator) == S.CLOSE
    runner(d, 'close-own', S.CLOSE, final=False)
    own = S.read_state(w, d, COMMIT, [h], [], BOOT, own_job=S.CLOSE, own_job_id='close-own')
    assert not own['broken'] and S.select(**own) == S.CLOSE
    assert own['used'] == set()                     # CLOSE is terminal, not a fallback slot


@pytest.mark.parametrize('passing_hold', [False, True])
@pytest.mark.parametrize('bad', ['missing', 'finished', 'wrong-job', 'wrong-commit', 'absolute',
                                 'other-window', 'suffix', 'missing-id', 'other-id', 'bad-commit',
                                 'bad-record', 'linked-record', 'unreadable-done'])
def test_close_own_admission_rejects_malformed_identity(tmp_path, passing_hold, bad):
    w, d, h = tmp_path/'w', tmp_path/'done', tmp_path/'hold'
    w.mkdir(), d.mkdir(), h.mkdir()
    touch(w, *full('rig-resume'), *full('rig-suspend'))
    if passing_hold:
        (h/'result.json').write_text(json.dumps(dict(ok=True, window=str(w))))
    commit, job_id = COMMIT, 'close-own'
    wrapper = {
        'absolute': '/abs/' + S.WRAPPER_PREFIX + 'CLOSE.sh',
        'other-window': 'docs/ai/x/designs/other/operator/CLOSE.sh',
        'suffix': S.WRAPPER_PREFIX + 'CLOSE.sh.extra',
    }.get(bad)
    if bad != 'missing':
        runner(d, job_id, S.WATCH_LOOP if bad == 'wrong-job' else S.CLOSE,
               final=bad == 'finished', commit='d' * 40 if bad == 'wrong-commit' else COMMIT, wrapper=wrapper)
    if bad == 'missing-id':
        job_id = None
    elif bad == 'other-id':
        job_id = 'another-close'
    elif bad == 'bad-commit':
        commit = 'C' * 40
    elif bad == 'bad-record':
        (d/'close-own.started.json').write_text('not json')
    elif bad == 'linked-record':
        (d/'close-own.started.json').rename(tmp_path/'target.json')
        (d/'close-own.started.json').symlink_to(tmp_path/'target.json')
    elif bad == 'unreadable-done':
        d = tmp_path/'absent-done'
    with pytest.raises(ValueError, match='CLOSE: unreadable runner state or invalid own record'):
        S.read_state(w, d, commit, [h], [], BOOT, own_job=S.CLOSE, own_job_id=job_id)


@pytest.mark.parametrize('state,expected', [('live', S.WATCH_LOOP), ('partial', S.CONTAIN_2),
                                           ('between', S.CONTAIN_2), ('stranded', S.HOLD_1)])
def test_close_identity_does_not_override_watcher_or_hold_selection(tmp_path, state, expected):
    w, d = tmp_path/'w', tmp_path/'done'
    w.mkdir(), d.mkdir()
    touch(w, *full('rig-resume'))
    if state in ('live', 'between'):
        touch(w, *full('city-resume'))
    if state == 'between':
        touch(w, *full('city-suspend'))
    if state == 'stranded':
        touch(w, 'city-resume-started.json')
    runner(d, 'close-own', S.CLOSE, final=False)
    own = S.read_state(w, d, COMMIT, [], [], BOOT, own_job=S.CLOSE, own_job_id='close-own')
    assert not own['broken'] and S.select(**own) == expected
    assert S.select(**S.read_state(w, d, COMMIT, [], [], BOOT)) == expected


def test_close_once_only_is_enforced_by_the_runner_and_final_record(tmp_path):
    import importlib.util
    import os
    spec = importlib.util.spec_from_file_location('jobrunner_close_test', RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)                  # read-only import, no runner process or host command
    w, d = tmp_path/'w', tmp_path/'done'
    w.mkdir(), d.mkdir()
    cfg = dict(stage=str(tmp_path), uid=os.getuid())
    wrapper = S.WRAPPER_PREFIX + 'CLOSE.sh'
    assert module.WRAPPER.fullmatch(wrapper)
    assert module.already_ran(cfg, COMMIT, wrapper) is None
    runner(d, 'close-own', S.CLOSE, final=False)
    assert S.select(**S.read_state(w, d, COMMIT, [], [], BOOT,
                                  own_job=S.CLOSE, own_job_id='close-own')) == S.CLOSE
    # The runner burns (commit, wrapper) at start: another id cannot re-open it, even after a refusal.
    assert module.already_ran(cfg, COMMIT, wrapper) == 'close-own'
    assert module.already_ran(cfg, 'd' * 40, wrapper) is None
    runner(d, 'close-own', S.CLOSE, exit_code=1)
    assert module.already_ran(cfg, COMMIT, wrapper) == 'close-own'
    with pytest.raises(ValueError, match='CLOSE:'):
        S.read_state(w, d, COMMIT, [], [], BOOT, own_job=S.CLOSE, own_job_id='close-own')


def test_close_guard_preserves_broken_hold_admission(tmp_path):
    w, d, h = tmp_path/'w', tmp_path/'done', tmp_path/'hold'
    w.mkdir(), d.mkdir(), h.mkdir()
    touch(w, *full('rig-resume'), *full('city-resume'))
    (d/'broken.json').write_text('not json')
    coordinator = S.read_state(w, d, COMMIT, [h], [], BOOT)
    assert coordinator['broken'] and S.select(**coordinator) == S.HOLD_1
    own_hold = S.read_state(w, d, COMMIT, [h], [], BOOT, own_job=S.HOLD_1, own_job_id='hold-own')
    assert own_hold['broken'] and S.select(**own_hold) == S.HOLD_1
    (h/'result.json').write_text(json.dumps(dict(ok=True, window=str(w))))
    coordinator = S.read_state(w, d, COMMIT, [h], [], BOOT)
    assert coordinator['broken'] and coordinator['hold_passed'] and S.select(**coordinator) == S.CLOSE
    # That coordinator selection grants no exception to CLOSE's own record check.
    with pytest.raises(ValueError, match='CLOSE:'):
        S.read_state(w, d, COMMIT, [h], [], BOOT, own_job=S.CLOSE, own_job_id='close-own')
