"""Generated r4 package checks only; no live commands or lifecycle operations."""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import types

import pytest

import retry


CACHE_NS = 1790587869654976784


def module(raw, name):
    value = types.ModuleType(name)
    value.__file__ = name + '.py'
    exec(compile(raw, value.__file__, 'exec'), value.__dict__)
    return value


@pytest.fixture(scope='module')
def built():
    _, before, out = retry.assemble(CACHE_NS)
    return before, out


def test_deterministic_and_exact_reviewed_parser(built):
    assert retry.assemble(CACHE_NS)[1:] == built
    contract = module(built[1]['contract.py'], 'r4_contract')
    status, census = (json.loads((retry.build.HERE/'fixtures'/name).read_bytes())
                      for name in ('zero-session-status.json', 'zero-session-census.json'))
    untouched = copy.deepcopy((status, census))
    for action in ('rig-resume', 'city-resume', 'rig-suspend', 'city-suspend'):
        assert contract.running_rows(status, census, action) == []
    assert (status, census) == untouched
    for bad in (None, True, '0', 0.0, -1, 1, 2):
        status['summary']['active_sessions'] = bad
        with pytest.raises(RuntimeError):
            contract.running_rows(status, census, 'rig-resume')


@pytest.mark.parametrize('pin', [None, True, '1790587869654976784', 0, -1,
                                  retry.successor.CACHE_NS - 1])
def test_invalid_or_regressive_cache_pin_refuses(pin):
    with pytest.raises(AssertionError, match='cache pin'):
        retry.assemble(pin)


def test_parser_review_cannot_be_claimed_for_changed_bytes(monkeypatch):
    original = retry.build.git
    def git(*args):
        raw = original(*args)
        if args[-1].endswith('/generators/contract.py'):
            return raw + b'\n# changed reviewed source\n'
        return raw
    monkeypatch.setattr(retry.build, 'git', git)
    with pytest.raises(AssertionError, match='reviewed parser source drift'):
        retry.assemble(CACHE_NS)


def test_recovered_image_bound_exactly_and_only_cache_time_pair_changes(built):
    w = module(built[1]['window-base-r11.py'], 'r4_window')
    assert str(w.ACCEPTED) == retry.PRIOR_TERMINAL + '/observed-after.json'
    assert w.ACCEPTED_SHA == retry.PRIOR_OBSERVATION_SHA
    prior = json.loads(w.read(w.ACCEPTED, w.ACCEPTED_SHA))
    result = json.loads(w.read(Path(retry.PRIOR_TERMINAL)/'result.json', retry.PRIOR_RESULT_SHA))
    assert all(result[k] is True for k in ('ok', 'accepted_restoration_bound', 'actual_host_verified'))
    assert result['worker_launched'] is False
    original = copy.deepcopy(prior)
    expected = copy.deepcopy(prior)
    for key in ('mtime_ns', 'ctime_ns'):
        assert expected['cache']['inventory'][w.CACHE_DIRECTORY][key] == retry.successor.CACHE_NS
        expected['cache']['inventory'][w.CACHE_DIRECTORY][key] = CACHE_NS
    assert w.approved_candidate_cache_image(prior) == expected
    assert prior == original
    bad = copy.deepcopy(prior)
    bad['cache']['inventory'][w.CACHE_DIRECTORY]['ctime_ns'] += 1
    with pytest.raises(RuntimeError, match='preimage'):
        w.approved_candidate_cache_image(bad)
    source = built[1]['window-base-r11.py'].decode()
    assert retry.PRIOR_TERMINAL + '/result.json' in source
    assert retry.PRIOR_RESULT_SHA in source
    assert 'previous window was not proven restored' in source


def test_all_fresh_roots_and_no_completed_operation_replay(built, tmp_path):
    before, out = built
    assert len(out) == 58
    for name in ('BIND', 'ROUTE'):
        path = tmp_path/(name + '.sh')
        path.write_bytes(out['operator/' + name + '.sh'])
        done = subprocess.run(['/bin/sh', str(path)], capture_output=True)
        assert done.returncode == 125 and done.stdout == b''
        assert b'replay prohibited' in done.stderr
    for name, raw in out.items():
        if name in ('window-base-r11.py', 'stranded-recovery.py'):
            continue
        for old in retry.ROOTS:
            assert old.encode() not in raw, (name, old)
    w = module(out['window-base-r11.py'], 'r4_fresh_window')
    assert str(w.ROOT) == '/var/tmp/ga-e0t1.20-window-20260928-r4'
    assert str(w.PREP) == '/var/tmp/ga-e0t1.20-prep-20260927-r1'
    assert str(w.WORK) == '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
    for name in ('WORKER-BRIEF.md', 'worker-startup.py', 'common-snapshot-r1.py',
                 'read-time-accounting.py', 'continuation-admission.py'):
        assert out[name] == before[name]
    historical = retry.build.git('show', retry.RECOVERY + ':' + retry.build.NEW + '/stranded-recovery.py')
    assert out['stranded-recovery.py'] == historical
    assert 'stranded-recovery.py' not in out['window-base-r11.py'].decode()


def test_literal_wrappers_and_dependency_hashes(built, tmp_path):
    out = built[1]
    for name, raw in out.items():
        if not name.endswith('.sh'):
            continue
        path = tmp_path/Path(name).name
        path.write_bytes(raw)
        assert subprocess.run(['/bin/sh', '-n', str(path)]).returncode == 0
        for script, variable in re.findall(r'"\$C/([a-z0-9-]+\.py)" "\$([A-Z_]+)"', raw.decode()):
            [pin] = re.findall(r'^%s=([0-9a-f]{64})$' % variable, raw.decode(), re.M)
            assert pin == hashlib.sha256(out[script]).hexdigest(), (name, script)
    stage = out['operator/STAGE.sh'].decode()
    assert stage.index('step audit-route ') < stage.index('step stage ')
    base = out['window-base-r11.py'].decode()
    assert base.index('.admit(') < base.index("save('preflight-pass.json'")
    assert base.index('.recheck(') < base.index("save('stage-consumed.json'")


def test_create_only_manifest_and_preserved_historical_bindings(built, tmp_path):
    output = tmp_path/'r4'
    retry.main(str(output), str(CACHE_NS))
    manifest = json.loads((output/'assembly.json').read_bytes())
    assert manifest['execution_admitted'] is False
    assert manifest['completed_operations_replayed'] is False
    assert manifest['parser_review_commit'] == retry.PARSER_REVIEW
    assert manifest['cache_pin_ns'] == CACHE_NS
    for name, pin in manifest['files'].items():
        raw = (output/name).read_bytes()
        assert raw == built[1][name] and hashlib.sha256(raw).hexdigest() == pin
    for name, pin in manifest['authoring_files'].items():
        assert hashlib.sha256((retry.build.HERE/name).read_bytes()).hexdigest() == pin
    for key, commit in (('consumed_attempt_files', retry.CONSUMED_ATTEMPT),
                        ('completed_recovery_files', retry.RECOVERY)):
        original = json.loads(retry.build.git('show', commit + ':' + retry.build.NEW + '/assembly.json'))
        assert manifest[key] == original['files']
    before = {str(p.relative_to(output)): p.read_bytes() for p in output.rglob('*') if p.is_file()}
    with pytest.raises(AssertionError, match='create-only'):
        retry.main(str(output), str(CACHE_NS))
    assert before == {str(p.relative_to(output)): p.read_bytes() for p in output.rglob('*') if p.is_file()}
