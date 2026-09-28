"""Pinned read-only R8 recovery and uninstalled R9 preparation tests."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import types

import pytest
import build
import permissions_baseline_r9 as permission
import recovered_claim_r9 as recovery
import startup_r9 as startup
import workspace_r9 as workspace


def read(path, pin):
    raw = Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pin
    return raw


def module(raw):
    value = types.ModuleType('fixture')
    exec(compile(raw, 'fixture', 'exec'), value.__dict__)
    return value


@pytest.fixture(scope='module')
def evidence():
    return {p: json.loads(read(p, pin)) for p, pin in recovery.PINS.items()}


def normalize(value):
    v = copy.deepcopy(value)
    if 'dependencies' in v:
        v['dependencies'] = sorted(v['dependencies'], key=lambda row: row['id'])
    return v


def test_exact_recovered_task(evidence):
    pair = recovery.expected_pair(evidence, normalize)
    assert pair['task']['status'] == 'open' and not pair['task'].get('assignee')
    assert pair['task']['metadata'] == recovery.CLOSED_METADATA
    assert pair['task']['notes'].endswith(recovery.STARTUP)
    assert pair['task']['updated_at'] == '2026-09-28T21:21:04Z'


@pytest.mark.parametrize('field', ['notes', 'description', 'acceptance', 'status', 'assignee',
                                 'metadata', 'started_at', 'updated_at'])
def test_recovered_claim_drift_refuses(evidence, field):
    bad = copy.deepcopy(evidence)
    p = recovery.CLOSE_ROOT/'16-claim-phase.json'
    rows = json.loads(bad[p]['stdout'])
    rows[0][field] = 'unexpected'
    bad[p]['stdout'] = json.dumps(rows)
    with pytest.raises(RuntimeError):
        recovery.expected_pair(bad, normalize)


@pytest.mark.parametrize('fault', ['exit', 'survivor', 'ack', 'census', 'result'])
def test_failed_recovery_evidence_refuses(evidence, fault):
    bad = copy.deepcopy(evidence)
    p = recovery.CLOSE_ROOT
    if fault == 'exit': bad[p/'16-claim-phase.json']['exit_code'] = 1
    elif fault == 'survivor': bad[p/'17-close-phase.json']['cleanup']['unexpected_survivors'] = True
    elif fault == 'ack': bad[p/'17-close-phase.json']['stdout'] = '{}'
    elif fault == 'census': bad[p/'18-sessions-phase.json']['stdout'] = '{"ok":true,"sessions":[{}]}'
    else: bad[p/'result.json']['worktree_processes'] = 1
    with pytest.raises(RuntimeError):
        recovery.expected_pair(bad, normalize)


def test_permission_rebinding_changes_only_two_exact_directory_times():
    old = json.loads(read(permission.POSTIMAGE, permission.POSTIMAGE_SHA))
    new = permission.expected_postimage(old)
    delta = [(path, key) for path in old for key in old[path]['stat']
             if old[path]['stat'][key] != new[path]['stat'][key]]
    assert delta == [(str(Path(permission.TRANSCRIPT).parent), 'ctime_ns'),
                     (str(Path(permission.TRANSCRIPT).parent), 'mtime_ns')]
    for path in old:
        assert old[path]['xattrs'] == new[path]['xattrs']
        assert old[path].get('sha256') == new[path].get('sha256')


def permission_fixture(monkeypatch):
    expected = permission.expected_postimage(json.loads(read(permission.POSTIMAGE, permission.POSTIMAGE_SHA)))
    current = copy.deepcopy(expected)
    current[permission.TRANSCRIPT] = dict(stat=copy.deepcopy(permission.TRANSCRIPT_STAT), xattrs={}, sha256=permission.TRANSCRIPT_SHA)
    history = json.loads(read(permission.HISTORY, permission.HISTORY_SHA))
    for section in history:
        for path in history[section]:
            if path in expected: history[section][path] = expected[path]['stat']
    history['sessions'][permission.TRANSCRIPT] = copy.deepcopy(permission.TRANSCRIPT_STAT)
    calls = []
    fake = types.SimpleNamespace(open_exact=lambda path, directory=False: path,
        image=lambda fd: current[fd], stable_identity=lambda *args: None,
        inventory=lambda root: history[Path(root).name])
    monkeypatch.setattr(permission.os, 'close', lambda fd: calls.append(fd))
    return current, history, calls, lambda *args: fake


def test_permission_guard_retains_all_exact_checks(monkeypatch):
    current, history, calls, loader = permission_fixture(monkeypatch)
    permission.verify(read, loader)
    assert len(calls) == 7
    original = copy.deepcopy(current)
    for field in ('mode', 'uid', 'gid', 'ino', 'dev', 'nlink', 'size', 'mtime_ns', 'ctime_ns'):
        current[permission.TRANSCRIPT]['stat'][field] += 1
        with pytest.raises(AssertionError): permission.verify(read, loader)
        current.clear()
        current.update(copy.deepcopy(original))
    current[permission.TRANSCRIPT]['sha256'] = '0' * 64
    with pytest.raises(AssertionError): permission.verify(read, loader)


def test_unknown_or_modified_historical_entry_refuses(monkeypatch):
    _, history, _, loader = permission_fixture(monkeypatch)
    history['sessions']['/home/loucmane/.codex/sessions/unexpected'] = {}
    with pytest.raises(AssertionError, match='historical inventory drift'):
        permission.verify(read, loader)


def test_frozen_probe_changes_only_fresh_evidence_path():
    out = startup.components()
    assert out['worker-startup-r9.py'].replace(b'/r9', b'/r8') == startup.frozen('worker-startup-r8.py')
    prompt = out['PRECLAIM-R9.md']
    assert prompt.count(startup.sha(out['worker-startup-r9.py']).encode()) == 3
    assert b'WAITING FOR SOURCE RELEASE:' in prompt and b'0600' in prompt and b'0700' in prompt
    assert b'exact r7 amendment' not in prompt


def test_prep_binds_recovery_and_preserves_all_typed_profiles():
    out = startup.components()
    text = out['prompt-prep-r9.py'].decode()
    assert startup.CLOSE in text and startup.CLOSE_SHA in text and startup.CLOSE_EXECUTOR in text
    assert "closed_session='ci-sgd80'" in text
    assert 'terminal-20260928-r8/result.json' in text
    assert 'startup-release-20260928-r8' in text
    assert "final['profiles']==before['profiles']" in text
    assert text.count('old._verify_host_assets()') == 2
    assert 'normalize_main(ROOT)' in text


def test_fresh_wrapper_signature_and_source_before_preparation():
    out = startup.components()
    raw = out['operator/PROMPT-PREP-R9.sh']
    assert b'COMPLETED OPERATION' not in raw
    assert startup.ROOT.encode() in raw
    assert startup.sha(out['prompt-prep-r9.py']).encode() in raw
    assert raw.index(b'verify-commit --raw') < raw.index(b'source-launch.py')
    assert subprocess.run(['/bin/sh', '-n'], input=raw, capture_output=True).returncode == 0


def test_deterministic_create_only_and_no_launch(tmp_path):
    assert startup.components() == startup.components()
    output = tmp_path/'prep'
    startup.main(str(output))
    manifest = json.loads((output/'prompt-prep-r9-manifest.json').read_bytes())
    assert not manifest['execution_admitted'] and not manifest['worker_launch_included']
    for name, pin in manifest['files'].items():
        assert startup.sha((output/name).read_bytes()) == pin
    with pytest.raises(AssertionError): startup.main(str(output))


def test_workspace_proof_reuses_strict_preserved_r8_validator():
    v = module(startup.frozen('startup-validation.py'))
    probe = module(startup.frozen('worker-startup-r8.py'))
    contract = module(startup.frozen('contract.py'))
    current = v.workspace_image(Path(v.WORK), probe.read_regular)
    w = types.SimpleNamespace(HERE=Path('/fixture'), read=read,
        module=lambda path, pin: v if pin == workspace.VALIDATOR_SHA else pytest.fail('wrong validator'))
    before = workspace.verify(w, current, contract.RUNTIME_IMAGE)
    assert len(workspace.PRIOR_FILES) == 6 and len(current) == len(before) + 3
    for path in workspace.PRIOR_FILES:
        bad = copy.deepcopy(current)
        bad[path]['sha256'] = '0' * 64
        with pytest.raises(RuntimeError): workspace.verify(w, bad, contract.RUNTIME_IMAGE)
