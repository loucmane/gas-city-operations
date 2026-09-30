"""Exact frozen historical absence is not a generic missing-Bead exception."""
import copy
import ast
import hashlib
import json

import pytest
from test_queue_preservation import fixture, add_owned, SESSION, p
from test_queue_guard import rig, load, HERE


def absent_fixture():
    q, b = fixture()
    row = q['dead'][0]
    absent = {row['id']: dict(bucket='dead', bead_id=row['bead_id'],
                             record_sha256=p.record_sha256(['dead', row]))}
    b = [x for x in b if x['id'] != row['bead_id']]
    return q, b, absent


def test_exact_missing_dead_baseline_and_future_preservation():
    q, b, a = absent_fixture()
    frozen = p.baseline(q, b, a)
    assert frozen['absent_dead'] == a
    assert p.preserve(frozen, q, b)['ok']
    add_owned(q, b)
    assert p.preserve(frozen, q, b, SESSION)['ok']


@pytest.mark.parametrize('defect', ['changed', 'moved', 'deleted', 'extra', 'pending', 'in_flight'])
def test_exception_requires_exact_complete_dead_tuple(defect):
    q, b, a = absent_fixture()
    row = q['dead'][0]
    if defect == 'changed': row['message'] = 'different'
    elif defect == 'moved': q['pending'].append(q['dead'].pop(0))
    elif defect == 'deleted': q['dead'].pop(0)
    elif defect == 'extra':
        b = [x for x in b if x['id'] != q['dead'][-1]['bead_id']]
    else:
        item = q[defect][0]
        a = {item['id']: dict(bucket=defect, bead_id=item['bead_id'],
                             record_sha256=p.record_sha256([defect, item]))}
    with pytest.raises(RuntimeError):
        p.baseline(q, b, a)


@pytest.mark.parametrize('alternative', [False, True])
def test_appearance_or_alternative_mapping_cannot_use_owned_exception(alternative):
    q, b, a = absent_fixture()
    frozen = p.baseline(q, b, a)
    row = q['dead'][0]
    b.append(dict(id='ci-alternative' if alternative else row['bead_id'],
        issue_type='chore', status='open', labels=['gc:nudge'],
        metadata=dict(nudge_id=row['id'], session_id=SESSION['id'],
                      continuation_epoch=SESSION['continuation_epoch'], agent='gascity/codex')))
    with pytest.raises(RuntimeError, match='historical shadow'):
        p.preserve(frozen, q, b, SESSION)
    with pytest.raises(RuntimeError, match='historical shadow'):
        p.baseline(q, b, a)


def test_absence_map_is_copied_and_generic_missing_still_refuses():
    q, b, a = absent_fixture()
    frozen = p.baseline(q, b, a)
    a.clear()
    assert len(frozen['absent_dead']) == 1
    with pytest.raises(RuntimeError, match='backing Bead missing'):
        p.baseline(q, b)


@pytest.mark.parametrize('value', [
    {}, {'count': False, 'schema_version': 1}, {'count': -1, 'schema_version': 1},
    {'count': 0, 'schema_version': 2}, {'count': 0.0, 'schema_version': 1},
])
def test_count_schema_fails_closed(value):
    g = load('queue-guard.py')
    with pytest.raises(RuntimeError):
        g.count_value(p, value)


def test_adapter_complete_census_and_exact_absence_commands(tmp_path, monkeypatch):
    g, w, s = rig(tmp_path, monkeypatch)
    q, b, a = absent_fixture()
    s.update(queue=q, beads=b)
    monkeypatch.setattr(g, 'absence', lambda w: a)
    assert g.checkpoint(w, 'preflight', None, None, None, capture=True, scoped=False)['ok']
    calls = [args[3:] for _, args in s['calls']]
    ids = ','.join(sorted(record['bead_id'] for record in a.values()))
    assert ['bd', 'count', '--id', ids, '--include-infra', '--json'] in calls
    assert ['bd', 'count', '--type', 'chore', '--label', 'gc:nudge', '--include-infra', '--json'] in calls
    labels = ','.join('nudge:'+identity for identity in sorted(a))
    assert ['bd', 'count', '--label-any', labels, '--include-infra', '--json'] in calls


@pytest.mark.parametrize('fault', ['truncated', 'appearance', 'malformed', 'transport'])
def test_adapter_never_infers_absence_from_bad_query(tmp_path, monkeypatch, fault):
    g, w, s = rig(tmp_path, monkeypatch)
    q, b, a = absent_fixture()
    s.update(queue=q, beads=b)
    monkeypatch.setattr(g, 'absence', lambda w: a)
    actual = w.phase
    def phase(label, args, *pos, **kw):
        if args[3:5] == ['bd', 'count']:
            if fault == 'transport': raise RuntimeError('query failure')
            if fault == 'malformed': return {'stdout': '{}'}
            if fault == 'truncated' and '--type' in args:
                return {'stdout': json.dumps(dict(count=len(b)+1, schema_version=1))}
            if fault == 'appearance' and '--id' in args:
                return {'stdout': json.dumps(dict(count=1, schema_version=1))}
        return actual(label, args, *pos, **kw)
    w.phase = phase
    with pytest.raises(RuntimeError):
        g.checkpoint(w, 'preflight', None, None, None, capture=True, scoped=False)
    assert not (g.WINDOW/'foreign-before.json').exists()
    assert (g.WINDOW/'foreign-preflight-failure.json').exists()


def test_manifest_is_pinned_and_provenance_is_not_execution_authority():
    g = load('queue-guard.py')
    raw = (HERE/'historical-shadow-absence.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == g.ABSENCE_SHA
    value = json.loads(raw)
    assert value['schema'] == 'ga-mb91.historical-shadow-absence.v1'
    assert len(value['records']) == 25
    assert value['queue_sha256'] == '96f74c1fc18d1c401592bcce4716c72a950588f3c7e9b75c0345a982c640ec28'
    assert len(value['exact_absence_proofs']) == 25
    assert value['worker_release'] is False
    assert all(set(record) == {'bucket', 'bead_id', 'record_sha256'}
               for record in value['records'].values())


def test_manifest_digest_mismatch_refuses_before_any_query(tmp_path):
    g = load('queue-guard.py')
    from types import SimpleNamespace
    w = SimpleNamespace(HERE=tmp_path, require=p.require, read=lambda path:b'{}')
    with pytest.raises(RuntimeError, match='historical absence digest'):
        g.absence(w)


def test_failed_preflight_disposition_preserves_exact_evidence_without_dispatch():
    helper = (HERE/'preserve-preflight-refusal.py').read_text()
    ast.parse(helper)
    assert "'ga-mb91-preflight-r1':'60bfdcc0761767f1e81a692e19f43e068efae009'" in helper
    assert 'EXPECTED_EXIT=1' in helper
    assert hashlib.sha256((HERE/'PREFLIGHT-REFUSAL-R1.json').read_bytes()).hexdigest() in helper
    assert "assert set(p.name for p in failed.iterdir())==set(expected)" in helper
    assert "done['unit_state_after']=='inactive'" in helper
    assert "cleanup['owned_process_group_gone']" in helper
    assert "assert not os.path.lexists('/var/tmp/ga-mb91-window-20260930-r2')" in helper
    assert 'submit_job' not in helper and 'systemd-run' not in helper
    assert "rename(directory,b'HALTED',directory,archive.encode(),1)" in helper


def test_fresh_window_root_is_shared_and_completed_bind_unchanged():
    g = load('queue-guard.py')
    assert str(g.WINDOW) == '/var/tmp/ga-mb91-window-20260930-r3'
    for name in ('window-base.py', 'window.py', 'release-runtime-r13.py'):
        raw = (HERE/name).read_bytes()
        assert b'ga-mb91-window-20260930-r1' not in raw
        assert b'ga-mb91-window-20260930-r2' not in raw
        assert b'ga-mb91-window-20260930-r3' in raw
    assert hashlib.sha256((HERE/'bind-task.py').read_bytes()).hexdigest() == '028ccef1db747088c7f8552c86094ded85b5db12f1d58d890bd7678fa432adea'


@pytest.mark.parametrize('owned_alias', [False, True])
def test_label_alias_with_wrong_metadata_refuses_before_ownership(owned_alias):
    q, b, a = absent_fixture()
    frozen = p.baseline(q, b, a)
    identity = next(iter(a))
    metadata = dict(nudge_id='nudge-eeeeeeeeeeee')
    if owned_alias:
        metadata.update(session_id=SESSION['id'], continuation_epoch=SESSION['continuation_epoch'],
                        agent='gascity/codex')
    b.append(dict(id='ci-labelalias', issue_type='chore', status='open',
                  labels=['gc:nudge', 'nudge:'+identity], metadata=metadata))
    with pytest.raises(RuntimeError, match='historical shadow'):
        p.baseline(q, b, a)
    with pytest.raises(RuntimeError, match='historical shadow'):
        p.preserve(frozen, q, b, SESSION)


@pytest.mark.parametrize('kind', ['retyped', 'missing-class-label', 'wrong-metadata-owned'])
def test_native_fallback_count_catches_aliases_outside_filtered_census(tmp_path, monkeypatch, kind):
    g, w, s = rig(tmp_path, monkeypatch)
    q, b, a = absent_fixture()
    s.update(queue=q, beads=b)
    monkeypatch.setattr(g, 'absence', lambda w: a)
    actual = w.phase
    def phase(label, args, *pos, **kw):
        if args[3:5] == ['bd', 'count'] and '--label-any' in args:
            # Models a native hit independent of its type, class labels,
            # metadata or owner. It remains invisible to the filtered census.
            return {'stdout': json.dumps(dict(count=1, schema_version=1))}
        return actual(label, args, *pos, **kw)
    w.phase = phase
    with pytest.raises(RuntimeError, match='historical shadow label'):
        g.checkpoint(w, 'preflight', None, None, None, capture=True, scoped=False)
    assert not (g.WINDOW/'foreign-before.json').exists()
    assert (g.WINDOW/'foreign-preflight-failure.json').exists()
