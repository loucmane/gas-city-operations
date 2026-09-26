"""Tests for the ga-sh3w (first Operations candidate window) ninth-successor package.

  python3 -m pytest -q designs/ga-sh3w-window/test_successor.py

Read-only: the package, the generator and its source commit, the pinned live files and build roots, one confined
`gc config show` / `gc order list` / `gc bd show` (all with GIT_OPTIONAL_LOCKS=0) and git reads of the canonical
Operations repository with no optional locks.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import types

import pytest

HERE = Path(__file__).parent
GEN = HERE/'generators'/'make_successor.py'
ENV = dict(HOME='/home/loucmane', USER='loucmane', LOGNAME='loucmane', LANG='C.UTF-8', GIT_OPTIONAL_LOCKS='0',
           GC_HOME='/home/loucmane/gascity/home', PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    module = types.ModuleType(name); module.__file__ = str(path)
    exec(compile(Path(path).read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


@pytest.fixture(scope='module')
def g():
    return load(GEN, 'make_successor')


@pytest.fixture(scope='module')
def generated(g):
    with tempfile.TemporaryDirectory() as tmp:
        g.main(tmp)
        yield {str(p.relative_to(tmp)): p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()}


def package_files():
    skip = {'test_successor.py', 'README.md'}
    return {str(p.relative_to(HERE)): p.read_bytes() for p in HERE.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.parts[len(HERE.parts)] != 'generators'
            and str(p.relative_to(HERE)) not in skip}


def test_package_is_the_generator_output(generated):
    assert package_files() == generated


def test_scripts_compile_and_shell_parses():
    for path in HERE.glob('*.py'):
        compile(path.read_bytes(), str(path), 'exec', dont_inherit=True)
    for path in (HERE/'operator').glob('*.sh'):
        assert subprocess.run(['/bin/sh', '-n', str(path)]).returncode == 0, path
        assert os.stat(path).st_mode & 0o111, path


def test_no_signing_lane_leftovers():
    for name, raw in package_files().items():
        text = raw.decode()
        for token in ('implementation-worker', 'gascity-core-worktrees', '2940569', 'release-r11.py',
                      'SIGNING-RELEASE', 'SOURCE-RELEASE', '7e008d9b', '334cc3c9', '7f335ad8', 'Core worktree'):
            assert token not in text, (name, token)
        # The signing provider name; the M9 signing wrapper path gct-claude-signing-worker is legitimate.
        assert not re.search(r'(?<!gct-)claude-signing', text), name
    assert not (HERE/'release-r11.py').exists() and not list((HERE/'operator').glob('*RELEASE*'))


def test_every_output_root_has_one_date():
    """All /var/tmp/ga-sh3w-* roots, %s-formatted ones included, carry the fresh date (s1 review B must_fix 1)."""
    roots = set()
    for name, raw in package_files().items():
        roots |= set(re.findall(r"/var/tmp/ga-sh3w-[A-Za-z0-9%<>_-]*?-(\d{8})-r\d", raw.decode()))
    assert roots == {'20260926'}, roots
    audit = (HERE/'audit-queue-r3.py').read_text()
    assert "ROOT = Path('/var/tmp/ga-sh3w-audit-%s-20260926-r1' % MODE)" in audit
    for wrapper, mode in (('ROUTE.sh', 'route'), ('RESUME.sh', 'route'), ('RESUME.sh', 'resume')):
        assert '/var/tmp/ga-sh3w-audit-%s-20260926-r1' % mode in (HERE/'operator'/wrapper).read_text(), (wrapper, mode)


def test_wrappers_bind_their_scripts():
    """Every 64-hex constant a wrapper names for a package script equals that script's digest."""
    for wrapper in (HERE/'operator').glob('*.sh'):
        text = wrapper.read_text()
        for script in re.findall(r'"\$C/([a-z0-9-]+\.py)" "\$([A-Z_]+)"', text):
            name, var = script
            [value] = re.findall(r'^%s=([0-9a-f]{64})$' % var, text, re.M)
            assert value == sha(HERE/name), (wrapper.name, name)


def test_identity_and_epoch(g):
    base = (HERE/'window-base-r11.py').read_text()
    assert "WORK = Path('/home/loucmane/gas-city-ops-candidate-worktrees/ga-sh3w')" in base
    assert "BASE = '040139d8738a025cbb5afcc8170b700292c5016e'" in base
    assert "ADMIN = Path('/home/loucmane/gas-city-ops/.git/worktrees/ga-sh3w')" in base
    assert "('core','995924','163987392096'), ('signer','2310','39660502')" in base
    assert "('broker','2940285','123477220085')" in base
    assert "return 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'" in base
    assert base.count('995924') == 3  # the host epoch, the status controller and the reload trace
    for name in ('window-r11.py', 'route-chain-r1.py'):
        assert '995924' in (HERE/name).read_text(), name
    for name in ('route-task-r5.py', 'watch-r11.py', 'close-r11.py', 'audit-queue-r3.py'):
        assert 'gascity/operations-candidate-worker' in (HERE/name).read_text(), name
    audit = (HERE/'audit-queue-r3.py').read_text()
    assert "ALIASES = {TARGET, 'operations-candidate-worker', 'gascity--operations-candidate-worker'}" in audit
    assert "'gascity--operations-candidate-worker-'" in audit and "'s-'" in audit


def test_hardened_candidate_git():
    base = (HERE/'window-base-r11.py').read_text()
    assert "'GIT_CONFIG_NOSYSTEM=1','GIT_CONFIG_GLOBAL=/dev/null','GIT_ATTR_NOSYSTEM=1'" in base
    assert "'-c','core.attributesFile=/dev/null'" in base
    assert "'--git-dir=/home/loucmane/gas-city-ops/.git/worktrees/ga-sh3w'" in base
    assert "HARDENED+['rev-parse','--verify','HEAD^{commit}']" in base
    assert "HARDENED+['status','--porcelain=v1','--ignored','--untracked-files=all']" in base
    assert "['/usr/bin/git','-C',str(WORK)" not in base
    watch = (HERE/'watch-r11.py').read_text()
    assert 'git = list(w.HARDENED)' in watch and "'-C', str(w.WORK)" not in watch
    assert watch.count("'--no-textconv', '--no-ext-diff'") == 2


def test_live_pins(g):
    pins = [(g.WITNESS_NEW), (g.INPUT_NEW), (g.ACCEPTED_NEW), g.COMPOSE_NEW,
            (g.FINALIZE_NEW[0] + '/compose', g.FINALIZE_NEW[1]),
            (g.INSPECTOR_NEW[0] + '/platform-inspect', g.INSPECTOR_NEW[1]),
            (g.INSPECTOR_NEW[0] + '/build-result.json', g.INSPECTOR_NEW[2]),
            ('/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json', g.RECEIPT_NEW),
            ('/home/loucmane/gascity/city/.gc/platform/install-manifest.json', g.M9_FILE),
            (g.ACCEPTED_NEW[0] + '.provider-pins', '82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b')]
    for path, digest in pins:
        assert sha(path) == digest, path
    record = json.loads(Path(g.INSPECTOR_NEW[0] + '/build-result.json').read_bytes())
    assert (record['core_commit'], record['core_tree'], record['entrypoint_sha256']) == (g.CORE_NEW, g.TREE_NEW,
                                                                                       g.INSPECTOR_NEW[3])
    receipt = json.loads(Path('/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json').read_bytes())
    assert [p['name'] for p in receipt['profiles']] == ['gascity/gc.implementation-worker', g.TARGET_NEW]
    assert receipt['permission_revision'] == g.REVISION_NEW
    accepted = json.loads(Path(g.ACCEPTED_NEW[0]).read_bytes())
    entry = accepted['cache']['inventory']['954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git']
    assert entry['mtime_ns'] == entry['ctime_ns'] == g.CACHE_P10_NS


def test_reviewed_candidate_tools_and_process_record():
    route = (HERE/'route-task-r5.py').read_text()
    for var in ('PREROUTE', 'CANDIDATE_GIT', 'RECORD'):
        [path] = re.findall(r"^%s=Path\('([^']+)'\)$" % var, route, re.M)
        [digest] = re.findall(r"^%s_SHA='([0-9a-f]{64})'$" % var, route, re.M)
        assert sha(path) == digest, var
    record = json.loads(Path(re.findall(r"^RECORD=Path\('([^']+)'\)$", route, re.M)[0]).read_bytes())
    assert record['controller']['pid'] == 995924
    assert "checked=pr.check(Path('/home/loucmane/gas-city-ops-candidate-worktrees'),Path('/home/loucmane/gas-city-ops/.git'),'ga-sh3w'" in route
    assert route.index('preroute-bead') < route.index("argv=w.GC+['--rig','gascity','sling'")


def test_bind_writes_only_the_launch_contract(g):
    bind = (HERE/'bind-task-r4.py').read_text()
    code = bind.split('"""', 2)[2]
    assert "metadata={'gc.work_dir':WORK,'gc.check_path':CHECK}" in bind
    assert 'opt_' not in code and 'template_overrides' not in code and '--append-notes' not in code
    receipt = json.loads(Path('/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json').read_bytes())
    candidate = [p for p in receipt['profiles'] if p['name'] == g.TARGET_NEW][0]
    assert candidate['check_path']['path'] == g.CHECK_PATH and sha(g.CHECK_PATH) == candidate['check_path']['sha256']


def test_bead_description_is_the_reviewed_brief(g):
    run = subprocess.run(['/home/loucmane/gascity/bin/gc', '--city', '/home/loucmane/gascity/city', '--rig', 'gascity',
                          'bd', 'show', 'ga-sh3w', '--json'], env=ENV, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    [bead] = json.loads(run.stdout)
    assert hashlib.sha256(bead['description'].encode()).hexdigest() == g.DESCRIPTION_SHA
    brief = subprocess.run(['git', '--no-optional-locks', '-C', '/home/loucmane/gas-city-ops-worktrees/ga-6utp-ops-candidate-activation',
                            'show', '2067a406:docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/'
                            'designs/ga-cw-first-window/R3-brief.md'], capture_output=True, check=True).stdout
    assert hashlib.sha256(brief).hexdigest() == g.DESCRIPTION_SHA


def test_worktree_preconditions(g):
    ops = subprocess.run(['git', '--no-optional-locks', '-C', g.OPS, 'rev-parse', 'refs/heads/main'],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert ops == g.BASE_NEW
    root = Path(g.CANDIDATE_ROOT)
    if (root/'ga-sh3w').exists():
        pytest.skip('WORKTREE has run')
    assert root.is_dir() and not root.is_symlink() and os.listdir(root) == []
    assert not Path(g.ADMIN).exists()


def test_overlay_recomputes(g):
    """The PREP overlay digest, recomputed read-only from the live inputs by the generated build_overlay."""
    prep = load(HERE/'prep-r11.py', 'prep')
    city = prep.read(prep.CITY/'city.toml', prep.CITY_SHA)
    baseline = prep.config()
    orders = prep.confined([str(prep.GC), '--city', str(prep.CITY), 'order', 'list', '--json'])
    candidate, patches, names, target, selected = prep.build_overlay(city, baseline, orders)
    assert hashlib.sha256(candidate).hexdigest() == g.OVERLAY_NEW == prep.OVERLAY_SHA
    assert [p for p in patches if not p['suspended']] == [dict(dir='gascity', name='operations-candidate-worker',
        suspended=False, work_dir=g.WORK, min_active_sessions=0, max_active_sessions=1)]


PREP_ROOT = Path('/var/tmp/ga-sh3w-prep-20260926-r1')


def test_prep_outputs_are_pinned(g):
    """s2: window-base pins exactly the ga-sh3w PREP outputs (PREP PASS 2026-09-26 09:29:43Z)."""
    base = (HERE/'window-base-r11.py').read_text()
    result = json.loads((PREP_ROOT/'result.json').read_bytes())
    assert result['ok'] is True and result['installed'] is False and result['worker_launched'] is False
    assert result['only_unsuspended_city_core_agent'] == 'gascity/operations-candidate-worker'
    assert result['changed_receipt_fields'] == ['permission_revision', 'receipt_sha256']
    for value in (sha(PREP_ROOT/'city.isolated.toml'), sha(PREP_ROOT/'receipt.final.json'), result['revision_after'],
                  sha(PREP_ROOT/'result.json'), sha(PREP_ROOT/'orders.isolated.json')):
        assert "'%s'" % value in base, value
    assert result['city_after_sha256'] == sha(PREP_ROOT/'city.isolated.toml') == g.OVERLAY_NEW
    assert result['revision_before'] == g.REVISION_NEW and result['receipt_before_sha256'] == g.RECEIPT_NEW
    for stale in ('449346e3', 'c1761144', '2de85e1e', '9d59a0b4'):
        assert stale not in base, stale


def test_window_base_pins_run_against_the_live_prep():
    """pins() reads every PREP output and the nudge order script by digest, read-only."""
    w = load(HERE/'window-base-r11.py', 'window_base_pins')
    w.pins()


def test_cache_disposition_pins_the_live_value(g):
    """s2: the pinned value is the live pack-cache .git time now; the disposition moves only that entry."""
    live = os.lstat('/home/loucmane/gascity/home/cache/repos/954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git')
    assert live.st_mtime_ns == live.st_ctime_ns == g.CACHE_PINNED_NS == 1790415062719606803
    w = load(HERE/'window-base-r11.py', 'window_base_cache')
    prior = json.loads(Path(g.ACCEPTED_NEW[0]).read_bytes())
    image = w.approved_candidate_cache_image(prior)
    key = '954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git'
    assert image['cache']['inventory'][key]['mtime_ns'] == image['cache']['inventory'][key]['ctime_ns'] == g.CACHE_PINNED_NS
    image['cache']['inventory'][key] = prior['cache']['inventory'][key]
    assert image == prior
    changed = json.loads(json.dumps(prior))
    changed['cache']['inventory'][key]['mtime_ns'] += 1
    with pytest.raises(RuntimeError, match='preimage'):
        w.approved_candidate_cache_image(changed)


def test_observers_pin_the_m9_providers():
    """s2 review B must_fix 1: both observers accept exactly the live M9 provider list."""
    manifest = json.loads(Path('/home/loucmane/gascity/city/.gc/platform/install-manifest.json').read_bytes())
    providers = manifest['integrity']['providers']
    assert [p['name'] for p in providers] == ['claude-native', 'codex', 'claude', 'claude']
    assert [p['path'] for p in providers[2:]] == ['/home/loucmane/gas-city-template/bin/gct-claude-signing-worker',
                                                  '/home/loucmane/gas-city-template/bin/gct-claude-candidate-worker']
    assert providers[3]['sha256'] == 'e4442971fd3188208eaf22974aaaf55f949b8f51041775f041ecb00a66de92a3'
    for name in ('observe-integrity-r11.py', 'observe-terminal-r11.py'):
        text = (HERE/name).read_text()
        assert "==['claude-native','codex','claude','claude'],'provider inventory'" in text, name
        assert "'M9 provider pins'" in text and "==['claude-native','codex','claude'],'provider" not in text, name


def test_exclude_job_pins_the_live_preimage(g):
    """s2 review B must_fix 2: EXCLUDE appends exactly one line to the live common info/exclude."""
    before = Path('/home/loucmane/gas-city-ops/.git/info/exclude').read_bytes()
    task = (HERE/'exclude-task-r1.py').read_text()
    if hashlib.sha256(before).hexdigest() == g.EXCLUDE_AFTER:
        pytest.skip('EXCLUDE has run')
    assert hashlib.sha256(before).hexdigest() == g.EXCLUDE_BEFORE and before.endswith(b'\n')
    assert b'.claude/skills' not in before
    assert hashlib.sha256(before + b'**/.claude/skills/\n').hexdigest() == g.EXCLUDE_AFTER
    assert "BEFORE_SHA='%s'" % g.EXCLUDE_BEFORE in task and "AFTER_SHA='%s'" % g.EXCLUDE_AFTER in task
    bind = (HERE/'bind-task-r4.py').read_text()
    assert "EXCLUDE_SHA='%s'" % sha(HERE/'exclude-task-r1.py') in bind and 'exclude job result' in bind


def test_common_snapshot_tool_compares_the_control_surface(g):
    tool = (HERE/'common-snapshot-r1.py').read_text()
    assert "BASE='%s'" % g.BASE_NEW in tool and "BRANCH='refs/heads/%s'" % g.BRANCH in tool
    assert "for sub in ('hooks','info')" in tool and "entry(COMMON/'config')" in tool
