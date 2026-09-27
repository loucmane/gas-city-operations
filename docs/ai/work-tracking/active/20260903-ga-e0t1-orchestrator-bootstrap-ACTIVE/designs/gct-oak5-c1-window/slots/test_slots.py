import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slots as S  # noqa: E402

A = S.ACTIONS
PERMITTED = {(): ['rig-resume'], ('rig-resume',): ['city-resume', 'rig-suspend'],
             ('rig-resume', 'city-resume'): ['city-suspend'],
             ('rig-resume', 'city-resume', 'city-suspend'): ['rig-suspend']}
QUIET = dict(c1_closed=True, session_drain_ack_closed=True, census_empty=True, orphan_decision=False)
LIVE = dict(c1_closed=False, session_drain_ack_closed=False, census_empty=False, orphan_decision=False)
OBS = (None, QUIET, LIVE, dict(QUIET, orphan_decision=True), dict(QUIET, census_empty=False))


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
                        yield life, set(used), hold, obs


def test_total_and_never_a_used_job():
    for life, used, hold, obs in all_states():
        r = S.select(life, used, hold, obs)
        assert r in S.JOBS + (S.CLOSE, S.STOP)
        assert r not in used


def test_close_only_when_close_is_held():
    for life, used, hold, obs in all_states():
        if S.select(life, used, hold, obs) == S.CLOSE:
            assert S.close_held(life, hold), (life, used, hold, obs)


def test_stop_only_after_both_holds_used():
    for life, used, hold, obs in all_states():
        if S.select(life, used, hold, obs) == S.STOP:
            assert set(S.HOLDS) <= used and not hold


def test_stranded_goes_to_a_hold():
    for life, used, hold, obs in all_states():
        if hold:
            continue
        seq = S.completed(life)
        if any(v in (S.INCOMPLETE, S.FAILED) for v in life.values()) or seq not in S.VALID:
            assert S.select(life, used, hold, obs) in S.HOLDS + (S.STOP,)


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


PREFIX = '/home/loucmane/gas-city-ops-worktrees/x/docs/ai/work-tracking/active/y/designs/gct-oak5-c1-window/operator/'


def runner(done, job_id, job, final=True, exit_code=0):
    record = dict(job_id=job_id, admitted=True, job=dict(job_id=job_id, wrapper=PREFIX + job + '.sh', commit='c' * 40))
    (done/(job_id + '.started.json')).write_text(json.dumps(record))
    if final:
        (done/(job_id + '.json')).write_text(json.dumps(dict(record, exit=exit_code)))
        (done/(job_id + '.halted-cleared.json')).write_text('job finished, not json')


def test_read_state(tmp_path):
    w, d = tmp_path/'w', tmp_path/'done'
    w.mkdir(), d.mkdir()
    touch(w, *full('rig-resume'), *full('city-resume'), 'suspension-city-suspend-intent.json')
    runner(d, 'oak5-c1-watch', S.WATCH_LOOP, exit_code=137)
    (d/'x.refused-1.json').write_text('{}')
    h = tmp_path/'hold'
    h.mkdir()
    (h/'result.json').write_text(json.dumps(dict(ok=True, window='/elsewhere')))
    o1, o2 = tmp_path/'o1', tmp_path/'o2'
    o1.mkdir(), o2.mkdir()
    (o1/'final-observation.json').write_text(json.dumps(dict(QUIET, window=str(w), written_ns=2)))
    (o2/'final-observation.json').write_text(json.dumps(dict(LIVE, window=str(w), written_ns=1)))
    st = S.read_state(w, d, PREFIX, [h], [o2, o1])
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
        st = S.read_state(w, d, PREFIX, [], [], own_job_id='job%d' % n)
        assert not st['broken'] and S.select(**st) == job, job
        coordinator = S.read_state(w, d, PREFIX, [], [])
        assert job in coordinator['used']                      # started, unfinished: used for everyone else
        (d/('job%d.json' % n)).write_text((d/('job%d.started.json' % n)).read_text())
    # CONTAIN-2 at the partial RESUME.
    w2 = tmp_path/'w2'
    w2.mkdir()
    touch(w2, *full('rig-resume'))
    d2 = tmp_path/'done2'
    d2.mkdir()
    runner(d2, 'c2', S.CONTAIN_2, final=False)
    assert S.select(**S.read_state(w2, d2, PREFIX, [], [], own_job_id='c2')) == S.CONTAIN_2


def test_broken_inputs_stop(tmp_path):
    w = tmp_path/'w'
    w.mkdir()
    d = tmp_path/'done'
    assert S.read_state(w, d, PREFIX, [], [])['broken']                          # no done directory
    d.mkdir()
    assert S.read_state(w, d, 'relative/', [], [])['broken']                     # wrong prefix shape
    (d/'bad.json').write_text('not json')
    st = S.read_state(w, d, PREFIX, [], [])
    assert st['broken'] and S.select(**st) == S.STOP
    (d/'bad.json').unlink()
    (d/'odd.name.json').write_text('{}')
    assert S.read_state(w, d, PREFIX, [], [])['broken']                          # unknown record shape
    (d/'odd.name.json').unlink()
    runner(d, 'j', S.WATCH_LOOP)
    assert S.read_state(w, d, PREFIX, [], [], own_job_id='j')['broken']          # own run already final
    assert S.read_state(w, d, PREFIX, [], [], own_job_id='missing')['broken']    # own run never started


def test_hold_result_counts_only_for_this_window(tmp_path):
    w = tmp_path/'w'
    w.mkdir()
    d = tmp_path/'done'
    d.mkdir()
    h = tmp_path/'h'
    h.mkdir()
    (h/'result.json').write_text(json.dumps(dict(ok=True, window=str(w))))
    st = S.read_state(w, d, PREFIX, [h], [])
    assert st['hold_passed'] and S.select(**st) == S.CLOSE


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
    st = S.read_state(w, d, PREFIX, [], [tmp_path/'missing'])
    assert st['obs'] is None and st['used'] == set() and st['stranded']
    assert S.select(**st) == S.HOLD_1
    w2 = tmp_path/'w2'
    w2.mkdir()
    touch(w2, *full('rig-resume'), 'other-phase.json')                          # a phase without its start
    assert S.read_state(w2, d, PREFIX, [], [])['stranded']
    touch(w, 'suspension-city-resume-refused-after.json')
    assert S.read_state(w, d, PREFIX, [], [])['lifecycle']['city-resume'] == S.FAILED
