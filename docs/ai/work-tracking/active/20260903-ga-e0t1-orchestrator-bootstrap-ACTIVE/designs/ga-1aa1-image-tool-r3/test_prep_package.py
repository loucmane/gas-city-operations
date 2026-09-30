"""Offline contract tests. Never execute PREP, a worker probe, or a lifecycle job.

Production evidence is read-only input. Filesystem mutation tests use tmp_path;
mocked sandbox/subscription checks are control-flow proof, not live acceptance.
"""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path
import stat
import sys
import types

import pytest

HERE = Path(__file__).parent


def load(name):
    path = HERE/name
    m = types.ModuleType(name)
    m.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), m.__dict__)
    return m


@pytest.fixture
def prep():
    return load('prepare.py')


@pytest.fixture
def frozen():
    path = HERE.parent/'ga-e0t1.20-astra-bootstrap/inputs.json'
    return {k: base64.b64decode(v, validate=True) for k, v in json.loads(path.read_bytes()).items()}


def test_retarget_only_workspace(prep, frozen):
    changed = prep.retarget(frozen)
    for name in frozen:
        assert changed[name].replace(prep.WORK.encode(), prep.OLD_WORK.encode()) == frozen[name]
    for name in ('config.baseline.json', 'orders.baseline.json', 'window-restrictions.rules'):
        assert changed[name] is frozen[name] or changed[name] == frozen[name]


@pytest.mark.parametrize('name', ['city.window-r2.toml', 'city.window-r3.toml',
    'window-r2-declared-delta.json', 'config.baseline.json'])
def test_retarget_refuses_unexpected_occurrence(prep, frozen, name):
    frozen[name] += prep.OLD_WORK.encode()
    with pytest.raises(AssertionError):
        prep.retarget(frozen)


def test_retarget_refuses_replay_or_unknown_input(prep, frozen):
    with pytest.raises(AssertionError):
        prep.retarget(prep.retarget(frozen))
    frozen['extra'] = b''
    with pytest.raises(AssertionError):
        prep.retarget(frozen)


def test_real_seed_configuration_is_only_retarget_and_prompt(prep, frozen):
    # configure loads pinned modules/evidence but does not run host verification,
    # subprocesses, normalization, installation, worker startup or PREP main.
    old = prep.configure()
    baseline = json.loads(frozen['config.baseline.json'])
    orders = json.loads(frozen['orders.baseline.json'])
    overlay, patches, names, target, selected = old.build_overlay(
        old.read(old.CITY/'city.toml', old.CITY_SHA), baseline, orders)
    value = old.expected_config(baseline, selected, target, names)
    chosen = [a for a in value['config']['Agents'] if (a['Dir'], a['Name']) == ('gascity', 'codex')]
    assert len(chosen) == 1
    assert chosen[0]['WorkDir'] == prep.WORK and chosen[0]['WorkDirRoots'] == [prep.WORK]
    assert chosen[0]['PromptTemplate'] == str(prep.PROMPT)
    assert chosen[0]['OptionDefaults']['model'] == 'gpt-6-astra'
    assert chosen[0]['OptionDefaults']['effort'] == 'high'
    assert chosen[0]['OptionDefaults']['permission_mode'] == 'fail-fast'
    assert value['config']['Workspace']['MaxActiveSessions'] == 1
    assert old.ROOT == prep.ROOT and old.WORK == prep.WORK
    assert old.sha(overlay) == old.OVERLAY_SHA
    assert prep.OLD_WORK.encode() not in overlay
    assert str(prep.PROMPT).encode() in overlay
    assert len(patches) == len(selected) == 48
    assert 'nudge-on-route' not in names
    assert all(a['Suspended'] for a in value['config']['Agents']
        if a['Provider'] == 'codex-managed' and (a['Dir'], a['Name']) != ('gascity', 'codex'))
    with pytest.raises(AssertionError, match='frozen input drift'):
        old.build_overlay(old.read(old.CITY/'city.toml'), {}, orders)


def test_receipt_preserves_typed_profiles_and_only_native_revision(prep):
    before = dict(profiles=[dict(name=x) for x in ['gascity/gc.implementation-worker',
        'gascity/operations-candidate-worker', 'gas-city-template/gc.implementation-worker']],
        permission_revision='before', receipt_sha256='before', other='exact')
    after = dict(before, permission_revision='after', receipt_sha256='after')
    prep.receipt_contract(before, after, dict(permission_revision='after'))
    for bad in (dict(after, profiles=[]), dict(after, other='changed'),
                dict(after, permission_revision='wrong'), dict(after, extra=1)):
        with pytest.raises(AssertionError):
            prep.receipt_contract(before, bad, dict(permission_revision='after'))
    before['profiles'].append(before['profiles'][0])
    with pytest.raises(AssertionError):
        prep.receipt_contract(before, after, dict(permission_revision='after'))


@pytest.fixture
def permission_fixture():
    m = load('permissions-baseline.py')
    return m, [json.loads(p.read_bytes()) for p in (m.PRIOR/'images.json',
        m.PRIOR/'history.json', m.CAPTURE/'images.json', m.CAPTURE/'history.json')]


def test_permission_continuation_is_exact(permission_fixture):
    m, args = permission_fixture
    m.expected(*args)
    assert len(args[2]) == len(args[0]) + 1


@pytest.mark.parametrize('kind', ['missing', 'extra', 'historical', 'old-mode', 'day-inode',
    'day-timestamps', 'new-mode', 'new-size', 'new-digest', 'new-links', 'new-owner',
    'new-xattr', 'history-extra', 'history-removed', 'history-metadata'])
def test_permission_continuation_refuses_drift(permission_fixture, kind):
    m, args = permission_fixture
    old, history, images, current = args
    first = next(p for p in old if p != m.DAY)
    if kind == 'missing': images.pop(m.TRANSCRIPT)
    elif kind == 'extra': images['/extra'] = copy.deepcopy(images[first])
    elif kind == 'historical': images[first]['xattrs']['unknown'] = '00'
    elif kind == 'old-mode': images[first]['stat']['mode'] ^= 0o020
    elif kind == 'day-inode': images[m.DAY]['stat']['ino'] += 1
    elif kind == 'day-timestamps': images[m.DAY]['stat']['mtime_ns'] += 1
    elif kind == 'new-mode': images[m.TRANSCRIPT]['stat']['mode'] |= 0o020
    elif kind == 'new-size': images[m.TRANSCRIPT]['stat']['size'] += 1
    elif kind == 'new-digest': images[m.TRANSCRIPT]['sha256'] = '0'*64
    elif kind == 'new-links': images[m.TRANSCRIPT]['stat']['nlink'] += 1
    elif kind == 'new-owner': images[m.TRANSCRIPT]['stat']['uid'] = 0
    elif kind == 'new-xattr': images[m.TRANSCRIPT]['xattrs']['unknown'] = '00'
    elif kind == 'history-extra': current['sessions']['/extra'] = {}
    elif kind == 'history-removed': current['sessions'].pop(m.DAY)
    elif kind == 'history-metadata': current['sessions'][first] = {'tampered': True}
    with pytest.raises(AssertionError): m.expected(*args)


def test_transcript_reader_exception_is_one_exact_image(permission_fixture, monkeypatch):
    m, args = permission_fixture
    helper = types.SimpleNamespace(FIELDS=tuple(args[2][m.TRANSCRIPT]['stat']))
    fd = m.os.open(m.TRANSCRIPT, m.os.O_RDONLY | m.os.O_NOFOLLOW | m.os.O_NOATIME)
    try:
        assert m.completed_transcript_image(helper, fd) == args[2][m.TRANSCRIPT]
        monkeypatch.setattr(m, 'TRANSCRIPT_SIZE', m.TRANSCRIPT_SIZE+1)
        with pytest.raises(AssertionError): m.completed_transcript_image(helper, fd)
    finally: m.os.close(fd)


def test_fresh_worker_evidence_parent_is_created_in_disposable_fixture(tmp_path, monkeypatch):
    m = load('worker-startup.py')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(m, 'WORK', tmp_path)
    monkeypatch.setattr(m, 'OUT', tmp_path/'.gc/worker-evidence/ga-1aa1/r1')
    monkeypatch.setenv('GC_SESSION_ID', 'fixture-session')
    monkeypatch.setenv('GIT_OPTIONAL_LOCKS', '0')
    for key in m.OVERRIDES: monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(m, 'pin', lambda *a: None)
    monkeypatch.setattr(m, 'verified_hook', lambda: types.SimpleNamespace(startup_status=lambda s: None))
    def capture(argv):
        text = m.BASE if 'rev-parse' in argv else m.BRANCH if 'branch' in argv else (
            m.IDENTITY if 'login' in argv else '')
        return types.SimpleNamespace(returncode=0, stdout=text.encode(), stderr=b'')
    monkeypatch.setattr(m, 'capture', capture)
    monkeypatch.setattr(m, 'foreign_probe', lambda p: dict(denied=True, fixture=True))
    m.main('fixture-session')
    assert json.loads((m.OUT/'startup.json').read_bytes())['source_edit_released'] is False
    assert stat.S_IMODE(m.OUT.parent.stat().st_mode) == 0o700
    with pytest.raises(FileExistsError): m.main('fixture-session')


@pytest.mark.parametrize('kind', ['symlink', 'group-write', 'file'])
def test_worker_directory_refuses_unsafe_parent(tmp_path, kind):
    m = load('worker-startup.py')
    p = tmp_path/'entry'
    if kind == 'symlink': p.symlink_to(tmp_path, target_is_directory=True)
    elif kind == 'group-write': p.mkdir(mode=0o700); p.chmod(0o770)
    else: p.write_text('fixture')
    with pytest.raises(RuntimeError): m.directory(p)


def test_entrypoint_separates_host_proof_from_normalize_child(prep):
    tree = ast.parse((HERE/'prepare.py').read_bytes())
    entry = tree.body[-1]
    for argv, expected_calls in ((['prep.py'], ['host', 'main']),
            (['prep.py', 'normalize', str(prep.ROOT)], ['normalize']),
            (['prep.py', 'normalize', '/wrong'], [])):
        calls = []
        old = types.SimpleNamespace(_SOURCE_SHA='digest', read=lambda *a: b'bytes',
            _verify_host_assets=lambda: calls.append('host'), main=lambda: calls.append('main'),
            normalize_main=lambda root: calls.append('normalize'))
        ns = dict(__name__='__main__', __file__='prep.py', configure=lambda: old,
            Path=Path, ROOT=prep.ROOT, sys=types.SimpleNamespace(argv=argv))
        code = compile(ast.Module(body=[entry], type_ignores=[]), '<entry-fixture>', 'exec')
        if argv[-1] == '/wrong':
            with pytest.raises(AssertionError): exec(code, ns)
        else: exec(code, ns)
        assert calls == expected_calls


def test_all_local_digest_bindings(prep):
    for path, digest in ((prep.SEED, prep.SEED_SHA), (prep.PROMPT, prep.PROMPT_SHA),
        (HERE/'launch-contract.py', prep.HELPER_SHA), (HERE/'worker-startup.py', prep.PROBE_SHA),
        (HERE/'permissions-baseline.py', prep.PERMISSIONS_SHA), (prep.WORKTREE, prep.WORKTREE_SHA),
        (prep.TERMINAL, prep.TERMINAL_SHA), (prep.CLOSE, prep.CLOSE_SHA)):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_startup_probe_delta_is_identity_and_fresh_parent_only():
    prior = HERE.parent/'ga-e0t1-20-astra-window'
    raw = (prior/'worker-startup-r11.py').read_text()
    replacements = {
        'ga-e0t1.20': 'ga-1aa1', '/r11': '/r1',
        'ga-1aa1-bind-20260927-r1': 'ga-1aa1-bind-20260929-r1',
        'c6b789bbe6ff677dd04336803dbf2c2e017812ba': '5b981444bf7d687c0367da4ee3d111ff4b443ead',
        'codex/ga-1aa1-c1-close-admission': 'codex/ga-1aa1-handover-image-r3',
        'ga-e0t1-20-astra-window/launch-contract-r5.py': 'ga-1aa1-image-tool-r3/launch-contract.py',
        'cfd2467d3ce7c8600eb635d28a97249ccdc7bfa055386a423506d3f8e60edc7e':
            'c78bb0a08f2a26feed29b50a3c423c10d2b0713f3c686123e5d89336fdb0d92e',
        "(WORK/'.gc', WORK/'.gc/worker-evidence')": "(WORK/'.gc', WORK/'.gc/worker-evidence', OUT.parent)",
    }
    for before, after in replacements.items():
        assert before in raw
        raw = raw.replace(before, after)
    assert raw == (HERE/'worker-startup.py').read_text()
    assert (prior/'launch-contract-r5.py').read_text().replace('ga-e0t1.20', 'ga-1aa1') == (
        HERE/'launch-contract.py').read_text()


def test_wrapper_requires_exact_clean_signed_head_and_fresh_root(prep):
    wrapper = (HERE/'operator/PREP.sh').read_text()
    assert hashlib.sha256((HERE/'prepare.py').read_bytes()).hexdigest() in wrapper
    for required in ('--untracked-files=all', 'verify-commit --raw', '7720D1FE503A88EDECA61A6F0C7D823543E01875',
        '"$head" != "$COMMIT"', '[ ! -e "$OUT" ] && [ ! -L "$OUT" ]', '31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea'):
        assert required in wrapper
    assert str(prep.ROOT) in wrapper
    assert 'systemctl' not in wrapper and 'sling' not in wrapper


def test_preclaim_preserves_actual_same_session_release_and_candidate_only(prep):
    text = prep.PROMPT.read_text()
    assert 'ga-e0t1.20' not in text and 'AMEND' not in text
    assert 'gpg --version' in text and 'sandbox_permissions' not in text
    assert text.count(prep.PROBE_SHA) == 3
    for required in ('WAITING FOR SOURCE RELEASE: ga-1aa1 session=ACTUAL_SESSION_ID',
        'SOURCE RELEASE: ga-1aa1 session=ACTUAL_SESSION_ID', 'test_image_tool.py',
        'pins.json and make_pins.py must remain byte-identical', 'Do not close the Bead',
        'Run in the ordinary', 'sandbox', 'Do not stage'):
        if required == 'Do not stage':
            assert 'signing, staging, commit, push' in text
        else:
            assert required in text
