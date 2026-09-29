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
    monkeypatch.setattr(m, 'OUT', tmp_path/'.gc/worker-evidence/ga-5uc9/r1')
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
    monkeypatch.setattr(m, 'predecessor_read_proof', lambda: dict(read_only=True, fixture=True))
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


def test_launch_contract_is_mechanical_identity_rebinding():
    prior = HERE.parent/'ga-1aa1-image-tool-r3/launch-contract.py'
    assert prior.read_text().replace('ga-1aa1', 'ga-5uc9') == (HERE/'launch-contract.py').read_text()


def test_startup_keeps_all_existing_checks():
    prior = (HERE.parent/'ga-xyqo-c1-package/worker-startup.py').read_text()
    for old, new in [
        ('ga-xyqo-c1-package', 'ga-5uc9-c1-package'),
        ('ga-xyqo', 'ga-5uc9'),
        ('codex/ga-5uc9-c1-package', 'codex/ga-5uc9-c1-package'),
        ('833b4289c03b788f8e836c09ae73b2674e816d873fe4ba0587a2584b9af0d6b1',
         '7e8e57ccb552d6c6dce30a7d380e7e2af0cf3619ef06fb7f2740b4daeb810a6f'),
    ]:
        assert old in prior
        prior = prior.replace(old, new)
    assert (HERE/'worker-startup.py').read_text() == prior

def test_predecessor_read_proof_exact_objects(monkeypatch):
    m = load('worker-startup.py')
    root = HERE.parent/'gct-e8ex-window'
    calls = []
    def capture(argv):
        calls.append(argv)
        relative = argv[-1].split(m.PREDECESSOR_ROOT)[1]
        return types.SimpleNamespace(returncode=0, stdout=(root/relative).read_bytes(), stderr=b'')
    monkeypatch.setattr(m, 'capture', capture)
    result = m.predecessor_read_proof()
    assert result == dict(commit=m.PREDECESSOR, blobs=m.PREDECESSOR_INPUTS, read_only=True)
    assert len(calls) == 2
    for call in calls:
        assert call[:8] == ['/usr/bin/git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                            '-c', 'core.hooksPath=/dev/null', 'cat-file', 'blob']
        assert call[-1].startswith('1df3d47ee499b85928c6d34f1aec6e33d1ef2c25:')


@pytest.mark.parametrize('kind', ['denied', 'diagnostic', 'wrong-blob'])
def test_predecessor_read_refuses_before_edit(monkeypatch, kind):
    m = load('worker-startup.py')
    monkeypatch.setattr(m, 'capture', lambda argv: types.SimpleNamespace(
        returncode=1 if kind == 'denied' else 0,
        stderr=b'diagnostic' if kind == 'diagnostic' else b'',
        stdout=b'wrong'))
    with pytest.raises(RuntimeError): m.predecessor_read_proof()


def test_previous_exact_large_transcript_still_protected(permission_fixture):
    m, args = permission_fixture
    previous_path = HERE.parent/'ga-1aa1-image-tool-r3/permissions-baseline.py'
    assert hashlib.sha256(previous_path.read_bytes()).hexdigest() == (
        '971f5ffde5be045624e7df8d0b3b10b3658d5b1d10c9b12e9c3a3fb3e4ccfd45')
    previous = types.ModuleType('previous'); previous.__file__ = str(previous_path)
    exec(compile(previous_path.read_bytes(), str(previous_path), 'exec'), previous.__dict__)
    assert args[2][previous.TRANSCRIPT] == args[0][previous.TRANSCRIPT]
    helper = types.SimpleNamespace(FIELDS=tuple(args[2][previous.TRANSCRIPT]['stat']))
    fd = m.os.open(previous.TRANSCRIPT, m.os.O_RDONLY | m.os.O_NOFOLLOW | m.os.O_NOATIME)
    try:
        assert previous.completed_transcript_image(helper, fd) == args[2][previous.TRANSCRIPT]
    finally: m.os.close(fd)


def test_worker_scope_is_finite_create_only_and_bound(prep):
    scope = json.loads((HERE/'FILE-SCOPE.json').read_bytes())
    assert scope['modified_files'] == scope['deleted_files'] == []
    assert scope['worker_can_execute_live_package'] is False
    assert scope['root'].endswith('/gct-oak5-c1-window')
    assert len(scope['new_files']) == len(set(scope['new_files'])) == 52
    assert not set(scope['new_files']) & set(scope['preserved_files'])
    assert all(not (HERE.parent/'gct-oak5-c1-window'/name).exists() for name in scope['new_files'])
    assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in scope['new_files'])
    for name, digest in [('FILE-SCOPE.json', prep.SCOPE_SHA), ('WORKER-BRIEF.md', prep.BRIEF_SHA)]:
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest() == digest


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
    for required in ('WAITING FOR SOURCE RELEASE: ga-5uc9 session=ACTUAL_SESSION_ID',
        'SOURCE RELEASE: ga-5uc9 session=ACTUAL_SESSION_ID', 'FILE-SCOPE.json',
        'design, HANDOVER, slots, accepted image tool and every predecessor remain', 'Do not close the Bead',
        'Run in the ordinary', 'sandbox', 'Do not stage'):
        if required == 'Do not stage':
            assert 'signing, staging, commit, push' in text
        else:
            assert required in text


def test_previous_second_large_transcript_still_protected(permission_fixture):
    m, args = permission_fixture
    previous_path = HERE.parent/'ga-x2wz-c1-package/permissions-baseline.py'
    assert hashlib.sha256(previous_path.read_bytes()).hexdigest() == (
        '29b9e38fc676fa1e21a1ef94aa4b310f43bae5f0e268915eeba42a762aad3e15')
    previous = types.ModuleType('previous'); previous.__file__ = str(previous_path)
    exec(compile(previous_path.read_bytes(), str(previous_path), 'exec'), previous.__dict__)
    assert args[2][previous.TRANSCRIPT] == args[0][previous.TRANSCRIPT]
    helper = types.SimpleNamespace(FIELDS=tuple(args[2][previous.TRANSCRIPT]['stat']))
    fd = m.os.open(previous.TRANSCRIPT, m.os.O_RDONLY | m.os.O_NOFOLLOW | m.os.O_NOATIME)
    try:
        assert previous.completed_transcript_image(helper, fd) == args[2][previous.TRANSCRIPT]
    finally:
        m.os.close(fd)

@pytest.mark.parametrize('kind', ['workspace', 'branch', 'base', 'launched', 'terminal', 'close'])
def test_completed_receipts_refuse_identity_or_restoration_drift(prep, kind):
    records = {p: json.loads(p.read_bytes()) for p in (prep.WORKTREE, prep.TERMINAL, prep.CLOSE)}
    if kind == 'workspace': records[prep.WORKTREE]['worktree'] += '-foreign'
    elif kind == 'branch': records[prep.WORKTREE]['branch'] += '-foreign'
    elif kind == 'base': records[prep.WORKTREE]['base'] = '0'*40
    elif kind == 'launched': records[prep.WORKTREE]['worker_launched'] = True
    elif kind == 'terminal': records[prep.TERMINAL]['actual_host_verified'] = False
    elif kind == 'close': records[prep.CLOSE]['closed_session'] = 'unrelated'
    reader = types.SimpleNamespace(read=lambda path, digest: json.dumps(records[path]).encode())
    with pytest.raises(AssertionError): prep.prove_completed_inputs(reader)


def test_completed_worktree_latch_is_the_only_admitted_job():
    text = (HERE/'preserve-worktree-halt.py').read_text()
    tree = ast.parse(text)
    bindings = [n for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'JOB_COMMITS' for t in n.targets)]
    assert len(bindings) == 1
    assert ast.literal_eval(bindings[0].value) == {
        'ga-5uc9-worktree-r1': 'b5b68579e25353c5133f48bd781ff14e90ee826d'}
    for clause in ('EXPECTED_EXIT=0', "done['unit_state_after']=='inactive'",
                   "json.loads((ROOT/'state/runner.json').read_bytes())['state']=='halted'",
                   "assert not os.path.lexists(ROOT/'PAUSE')",
                   'no_job_queued=True', 'rename(directory'):
        assert clause in text



def test_prompt_is_only_reviewed_waiting_insertion_and_identity_rebinding(prep):
    proof = json.loads((HERE/'PRECLAIM-REBINDING.json').read_bytes())
    prior = (HERE.parent/proof['predecessor']).read_text()
    for old, new in proof['replacements']:
        assert old in prior
        prior = prior.replace(old, new)
    assert prior == prep.PROMPT.read_text()

def test_permission_reader_retains_both_previous_exact_readers():
    tree = ast.parse((HERE/'permissions-baseline.py').read_bytes())
    verify = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'verify')
    observe = next(n for n in verify.body if isinstance(n, ast.FunctionDef) and n.name == 'observe')
    assert len([n for n in observe.body if isinstance(n, ast.If)]) == 6
    assert ast.unparse(observe.body[-1]) == 'return m.image(fd)'

def test_prepare_is_exact_predecessor_rebinding():
    prior = (HERE.parent/'ga-e0t1-21-c1-package/prepare.py').read_text()
    for old, new in json.loads((HERE/'PREP-REBINDING.json').read_bytes()):
        assert old in prior
        prior = prior.replace(old, new)
    assert (HERE/'prepare.py').read_text() == prior


def test_immediate_predecessor_large_transcript_remains_protected(permission_fixture):
    m, args = permission_fixture
    path = HERE.parent/'ga-rq5n-c1-package/permissions-baseline.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        '470b0afc0cca1c55005f716676949e2a96f0dddd912be94fa5f3fd046bf1dc76')
    previous = types.ModuleType('immediate_predecessor')
    previous.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), previous.__dict__)
    assert args[2][previous.TRANSCRIPT] == args[0][previous.TRANSCRIPT]
    helper = types.SimpleNamespace(FIELDS=tuple(args[2][previous.TRANSCRIPT]['stat']))
    fd = m.os.open(previous.TRANSCRIPT, m.os.O_RDONLY | m.os.O_NOFOLLOW | m.os.O_NOATIME)
    try:
        assert previous.completed_transcript_image(helper, fd) == args[2][previous.TRANSCRIPT]
    finally:
        m.os.close(fd)


def test_latest_large_transcript_remains_protected(permission_fixture):
    m, args = permission_fixture
    path = HERE.parent/'ga-9olv-c1-package/permissions-baseline.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == '4428d83183beb88fb1b321b124fb1514c11f7e861afb6cf5c24242e7990e5371'
    previous = types.ModuleType('previous')
    previous.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), previous.__dict__)
    assert args[2][previous.TRANSCRIPT] == args[0][previous.TRANSCRIPT]
    helper = types.SimpleNamespace(FIELDS=tuple(args[2][previous.TRANSCRIPT]['stat']))
    fd = m.os.open(previous.TRANSCRIPT, m.os.O_RDONLY | m.os.O_NOFOLLOW | m.os.O_NOATIME)
    try:
        assert previous.completed_transcript_image(helper, fd) == args[2][previous.TRANSCRIPT]
    finally:
        m.os.close(fd)


def test_private_evidence_instruction_is_explicit(prep):
    prompt = prep.PROMPT.read_text()
    for text in ('O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW',
                 'O_CLOEXEC and mode 0o600', 'write and fsync',
                 'Do not use Path.write_text', 'umask 0o077',
                 'precreate its output logs and JUnit file at 0600',
                 'Do not chmod existing files', 'Use fresh output names'):
        assert text in prompt


@pytest.mark.parametrize('mask', [0o002, 0o022, 0o077])
def test_private_creation_does_not_depend_on_inherited_umask(tmp_path, mask):
    m = load('worker-startup.py')
    old = m.os.umask(mask)
    path = tmp_path/'fresh-evidence.json'
    try:
        m.exclusive(path, b'private evidence')
    finally:
        m.os.umask(old)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert path.read_bytes() == b'private evidence'
    with pytest.raises(FileExistsError):
        m.exclusive(path, b'not replacement')
    assert path.read_bytes() == b'private evidence'


def test_private_creation_refuses_symlink_without_touching_target(tmp_path):
    m = load('worker-startup.py')
    target = tmp_path/'target'
    target.write_bytes(b'preserved fixture')
    link = tmp_path/'link'
    link.symlink_to(target)
    before = target.stat()
    with pytest.raises(FileExistsError):
        m.exclusive(link, b'forbidden')
    assert target.read_bytes() == b'preserved fixture'
    assert target.stat().st_mtime_ns == before.st_mtime_ns


def test_partial_seed_is_exact_scope_and_explicitly_not_acceptance(prep):
    raw = (HERE/'PRESERVED-PARTIAL-INPUT.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '5dcc2bf7246f384e623eeca0c3a9692e8810ad17f91938ec8e3b09410953c6ce'
    partial = json.loads(raw)
    scope = json.loads((HERE/'FILE-SCOPE.json').read_bytes())
    assert partial['candidate_pass'] is False and partial['coordinator_executed_source'] is False
    assert partial['failed_evidence_included'] is False
    assert partial['source_task'] == 'ga-xyqo' and partial['task'] == 'ga-5uc9'
    assert partial['source_workspace'] == '/home/loucmane/gas-city-ops-candidate-worktrees/ga-xyqo'
    assert partial['source_base'] == '801a5a9d5b0d72f665c949a86573357f02c9f1ac'
    assert set(partial['inventory']) == {scope['root']+'/'+p for p in scope['new_files']}
    assert sum(row['size'] for row in partial['inventory'].values()) == partial['total_bytes'] == 750404
    brief = (HERE/'WORKER-BRIEF.md').read_text()
    for clause in ('Never execute old source during seeding', 'no-atime',
                   'The old 0664 evidence file stays untouched',
                   '12 previous RED failures and incomplete GREEN',
                   '52 partial source files'):
        assert clause in brief


def test_completed_xyqo_exact_transcript_remains_protected(permission_fixture):
    m, args = permission_fixture
    path = HERE.parent/'ga-xyqo-c1-package/permissions-baseline.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == '2074e4bf524d6c0e0e182970ac8c197f9734fc726e17029010121672610c0ccd'
    previous = types.ModuleType('xyqo_permissions')
    previous.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), previous.__dict__)
    assert args[2][previous.TRANSCRIPT] == args[0][previous.TRANSCRIPT]
    helper = types.SimpleNamespace(FIELDS=tuple(args[2][previous.TRANSCRIPT]['stat']))
    fd = m.os.open(previous.TRANSCRIPT, m.os.O_RDONLY | m.os.O_NOFOLLOW | m.os.O_NOATIME)
    try:
        assert previous.completed_transcript_image(helper, fd) == args[2][previous.TRANSCRIPT]
    finally:
        m.os.close(fd)
