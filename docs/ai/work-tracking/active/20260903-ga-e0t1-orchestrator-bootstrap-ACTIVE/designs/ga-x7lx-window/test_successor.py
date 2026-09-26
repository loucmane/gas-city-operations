"""Tests for the ga-x7lx (ga-fsfg R3 retry) tenth-successor window package.

  python3 -m pytest -q designs/ga-x7lx-window/test_successor.py

Read-only: the package, the generator and its source commit, the pinned live files and build roots, one confined
`gc config show` / `gc order list` and `gc bd show` reads (all with GIT_OPTIONAL_LOCKS=0) and git reads of the
canonical Operations repository with no optional locks.
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
CACHE_KEY = '954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git'
RECEIPT = '/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json'


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


def bead(name):
    run = subprocess.run(['/home/loucmane/gascity/bin/gc', '--city', '/home/loucmane/gascity/city', '--rig', 'gascity',
                          'bd', 'show', name, '--json'], env=ENV, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    [row] = json.loads(run.stdout)
    return row, run.stdout


def test_package_is_the_generator_output(generated):
    assert package_files() == generated


def test_scripts_compile_and_shell_parses():
    for path in HERE.glob('*.py'):
        compile(path.read_bytes(), str(path), 'exec', dont_inherit=True)
    for path in (HERE/'operator').glob('*.sh'):
        assert subprocess.run(['/bin/sh', '-n', str(path)]).returncode == 0, path
        assert os.stat(path).st_mode & 0o111, path


def test_no_leftovers():
    """No signing-lane, ga-qcwl-era or EXCLUDE residue; ga-sh3w appears only as the named predecessor."""
    for name, raw in package_files().items():
        text = raw.decode()
        for token in ('implementation-worker', 'gascity-core-worktrees', '2940569', 'release-r11.py',
                      'SIGNING-RELEASE', 'SOURCE-RELEASE', '7e008d9b', '334cc3c9', '7f335ad8', 'Core worktree',
                      'exclude-task-r1.py', 'EXCLUDE.sh', 'CACHE_P10_NS'):
            assert token not in text, (name, token)
        assert not re.search(r'(?<!gct-)claude-signing', text), name
        for line in text.splitlines():
            if 'ga-sh3w' in line:
                assert name in ('window-base-r11.py', 'prep-r11.py', 'bind-task-r5.py'), (name, line)
                assert 'TERMINAL' in line or 'ga-sh3w-terminal-20260926-r1/observed-after.json' in line \
                    or 'r8 (ga-sh3w' in line or 'the ga-sh3w prep' in line \
                    or 'ga-sh3w EXCLUDE' in line or 'the ga-sh3w bind-task-r4.py' in line \
                    or 'the ga-sh3w outcome' in line, (name, line)
    assert not (HERE/'exclude-task-r1.py').exists() and not (HERE/'operator'/'EXCLUDE.sh').exists()


def test_every_output_root_is_fresh():
    """Every /var/tmp root the package writes is a ga-x7lx root with the one date; none exists yet except
    those the pre-window jobs create."""
    roots = set()
    for name, raw in package_files().items():
        roots |= set(re.findall(r"/var/tmp/ga-x7lx-[A-Za-z0-9%<>_-]*?-(\d{8})-r\d", raw.decode()))
    assert roots == {'20260926'}, roots
    audit = (HERE/'audit-queue-r3.py').read_text()
    assert "ROOT = Path('/var/tmp/ga-x7lx-audit-%s-20260926-r1' % MODE)" in audit
    for wrapper, mode in (('ROUTE.sh', 'route'), ('RESUME.sh', 'route'), ('RESUME.sh', 'resume')):
        assert '/var/tmp/ga-x7lx-audit-%s-20260926-r1' % mode in (HERE/'operator'/wrapper).read_text(), (wrapper, mode)


def test_wrappers_bind_their_scripts():
    """Every 64-hex constant a wrapper names for a package script equals that script's digest."""
    for wrapper in (HERE/'operator').glob('*.sh'):
        text = wrapper.read_text()
        for script in re.findall(r'"\$C/([a-z0-9-]+\.py)" "\$([A-Z_]+)"', text):
            name, var = script
            [value] = re.findall(r'^%s=([0-9a-f]{64})$' % var, text, re.M)
            assert value == sha(HERE/name), (wrapper.name, name)
    assert 'bind-task-r5.py' in (HERE/'operator'/'BIND.sh').read_text()


def test_identity_and_epoch():
    base = (HERE/'window-base-r11.py').read_text()
    assert "WORK = Path('/home/loucmane/gas-city-ops-candidate-worktrees/ga-x7lx')" in base
    assert "BASE = '040139d8738a025cbb5afcc8170b700292c5016e'" in base
    assert "ADMIN = Path('/home/loucmane/gas-city-ops/.git/worktrees/ga-x7lx')" in base
    assert "'--git-dir=/home/loucmane/gas-city-ops/.git/worktrees/ga-x7lx'" in base
    assert "('core','995924','163987392096'), ('signer','2310','39660502')" in base
    assert "('broker','2940285','123477220085')" in base
    assert "return 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'" in base
    for name in ('route-task-r5.py', 'watch-r11.py', 'close-r11.py', 'audit-queue-r3.py'):
        assert 'gascity/operations-candidate-worker' in (HERE/name).read_text(), name
    route = (HERE/'route-task-r5.py').read_text()
    assert "sling',TARGET,'ga-x7lx','--no-formula','--no-convoy','--json']" in route
    worktree = (HERE/'worktree-task-r1.py').read_text()
    assert "BRANCH='codex/ga-x7lx-delivery-class'" in worktree and "ROOT=Path('/var/tmp/ga-x7lx-worktree-20260926-r1')" in worktree


def test_accepted_image_is_the_sh3w_terminal_record(g):
    """The predecessor's TERMINAL observed-after record is the accepted image, compared on four keys only."""
    base = (HERE/'window-base-r11.py').read_text()
    assert "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\n" % g.ACCEPTED_NEW in base
    assert "ACCEPTED_KEYS = ('cache', 'host', 'pins', 'protected')" in base
    assert "PROVIDER = Path('%s')\nPROVIDER_SHA = '%s'\n" % g.PROVIDER in base
    assert "image = approved_candidate_cache_image({key: prior[key] for key in ACCEPTED_KEYS})" in base
    assert "accepted_provider=json.loads(read(PROVIDER,PROVIDER_SHA))" in base
    assert sha(g.ACCEPTED_NEW[0]) == g.ACCEPTED_NEW[1] and sha(g.PROVIDER[0]) == g.PROVIDER[1]
    record = json.loads(Path(g.ACCEPTED_NEW[0]).read_bytes())
    assert {'cache', 'host', 'pins', 'protected'} <= set(record)
    entry = record['cache']['inventory'][CACHE_KEY]
    assert entry['mtime_ns'] == entry['ctime_ns'] == g.CACHE_PREV_NS
    # The TERMINAL result that produced it passed: preservation, restoration binding and zero inspector drifts.
    result = json.loads(Path('/var/tmp/ga-sh3w-terminal-20260926-r1/result.json').read_bytes())
    assert result['ok'] is True and result['window_preservation'] is True and result['worker_launched'] is False
    assert result['accepted_restoration_bound'] is True and result['report']['report'] == {'Drifts': None}


def test_cache_disposition_moves_only_the_one_entry(g):
    w = load(HERE/'window-base-r11.py', 'window_base_cache')
    prior = json.loads(Path(g.ACCEPTED_NEW[0]).read_bytes())
    image = {key: prior[key] for key in ('cache', 'host', 'pins', 'protected')}
    if g.CACHE_PINNED_NS is None:
        with pytest.raises(RuntimeError, match='not yet pinned'):
            w.approved_candidate_cache_image(image)
        w.CACHE_PINNED_NS = 1
    moved = w.approved_candidate_cache_image(image)
    entry = moved['cache']['inventory'][CACHE_KEY]
    assert entry['mtime_ns'] == entry['ctime_ns'] == w.CACHE_PINNED_NS
    moved['cache']['inventory'][CACHE_KEY] = image['cache']['inventory'][CACHE_KEY]
    assert moved == image
    changed = json.loads(json.dumps(image))
    changed['cache']['inventory'][CACHE_KEY]['mtime_ns'] += 1
    with pytest.raises(RuntimeError, match='preimage'):
        w.approved_candidate_cache_image(changed)


def test_live_pins(g):
    base = load(HERE/'window-base-r11.py', 'window_base_live')
    assert sha(base.WITNESS) == base.WITNESS_SHA
    assert sha(RECEIPT) == base.RECEIPT_SHA[0]
    assert sha('/home/loucmane/gascity/city/city.toml') == base.CITY_SHA[0]
    receipt = json.loads(Path(RECEIPT).read_bytes())
    assert [p['name'] for p in receipt['profiles']] == ['gascity/gc.implementation-worker', g.TARGET]
    assert receipt['permission_revision'] == base.REVISION[0]


def test_reviewed_candidate_tools_and_process_record():
    route = (HERE/'route-task-r5.py').read_text()
    for var in ('PREROUTE', 'CANDIDATE_GIT', 'RECORD'):
        [path] = re.findall(r"^%s=Path\('([^']+)'\)$" % var, route, re.M)
        [digest] = re.findall(r"^%s_SHA='([0-9a-f]{64})'$" % var, route, re.M)
        assert sha(path) == digest, var
    record = json.loads(Path(re.findall(r"^RECORD=Path\('([^']+)'\)$", route, re.M)[0]).read_bytes())
    assert record['controller']['pid'] == 995924
    assert ("checked=pr.check(Path('/home/loucmane/gas-city-ops-candidate-worktrees'),"
            "Path('/home/loucmane/gas-city-ops/.git'),'ga-x7lx'") in route
    assert route.index('preroute-bead') < route.index("argv=w.GC+['--rig','gascity','sling'")


def test_bind_writes_only_the_launch_contract(g):
    bind = (HERE/'bind-task-r5.py').read_text()
    code = bind.split('"""', 2)[2]
    assert "metadata={'gc.work_dir':WORK,'gc.check_path':CHECK}" in bind
    assert 'opt_' not in code and 'template_overrides' not in code and '--append-notes' not in code
    assert "assert not before.get('dependencies'),'unexpected Bead edge'" in bind
    assert "DESCRIPTION_SHA='%s'" % g.DESCRIPTION_SHA in bind
    assert "EXCLUDE_AFTER='%s'" % g.EXCLUDE_AFTER in bind
    route = (HERE/'route-task-r5.py').read_text()
    assert "DESCRIPTION_SHA='%s'" % g.DESCRIPTION_SHA in route and "BIND_SHA='%s'" % sha(HERE/'bind-task-r5.py') in route
    receipt = json.loads(Path(RECEIPT).read_bytes())
    candidate = [p for p in receipt['profiles'] if p['name'] == g.TARGET][0]
    assert candidate['check_path']['path'] == g.CHECK_PATH and sha(g.CHECK_PATH) == candidate['check_path']['sha256']


def test_live_exclude_is_the_postimage(g):
    raw = Path(g.EXCLUDE).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == g.EXCLUDE_AFTER and raw.endswith(b'**/.claude/skills/\n')


def test_brief_is_readable_and_reassembles_to_r12(g):
    """The operator decision: a short task brief and two spec holders, each view well under the inline limit."""
    task, raw = bead(g.BEAD)
    assert hashlib.sha256(task['description'].encode()).hexdigest() == g.DESCRIPTION_SHA
    assert task['status'] == 'open' and not task.get('dependencies') and not task.get('assignee')
    assert len(raw) < 25000
    parts = []
    for name, digest in g.SPECS:
        spec, spec_raw = bead(name)
        assert spec['status'] == 'closed' and not spec.get('dependencies') and len(spec_raw) < 25000, name
        assert hashlib.sha256(spec['description'].encode()).hexdigest() == digest, name
        assert '`bd show %s --json`' % name in task['description']
        parts.append(spec['description'].split('\n\n', 1)[1])
    text = task['description']
    head = text[:text.index('## The full specification (read first)')]
    tail = text[text.index('## Working rules'):]
    assert hashlib.sha256((head + ''.join(parts) + tail).encode()).hexdigest() == g.BRIEF_SHA
    brief = subprocess.run(['git', '--no-optional-locks', '-C', '/home/loucmane/gas-city-ops-worktrees/ga-6utp-ops-candidate-activation',
                            'show', '2067a406:docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/'
                            'designs/ga-cw-first-window/R3-brief.md'], capture_output=True, check=True).stdout
    assert hashlib.sha256(brief).hexdigest() == g.BRIEF_SHA


def test_worktree_preconditions(g):
    ops = subprocess.run(['git', '--no-optional-locks', '-C', g.OPS, 'rev-parse', 'refs/heads/main'],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert ops == g.BASE
    listing = subprocess.run(['git', '--no-optional-locks', '-C', g.OPS, 'worktree', 'list', '--porcelain'],
                             capture_output=True, text=True, check=True).stdout
    retired = '/home/loucmane/.local/share/gas-city-staging/candidate-archive/ga-sh3w/ga-sh3w'
    block = listing[listing.index('worktree ' + retired):].split('\n\n', 1)[0]
    assert 'locked gct-lagl retired candidate' in block
    root = Path(g.CANDIDATE_ROOT)
    if (root/'ga-x7lx').exists():
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


def test_observers_pin_the_m9_providers():
    manifest = json.loads(Path('/home/loucmane/gascity/city/.gc/platform/install-manifest.json').read_bytes())
    providers = manifest['integrity']['providers']
    assert [p['name'] for p in providers] == ['claude-native', 'codex', 'claude', 'claude']
    assert providers[3]['sha256'] == 'e4442971fd3188208eaf22974aaaf55f949b8f51041775f041ecb00a66de92a3'
    for name in ('observe-integrity-r11.py', 'observe-terminal-r11.py'):
        text = (HERE/name).read_text()
        assert "==['claude-native','codex','claude','claude'],'provider inventory'" in text, name
        assert "'M9 provider pins'" in text, name


def test_common_snapshot_tool_compares_the_control_surface(g):
    tool = (HERE/'common-snapshot-r1.py').read_text()
    assert "BASE='%s'" % g.BASE in tool and "BRANCH='refs/heads/%s'" % g.BRANCH in tool
    assert "for sub in ('hooks','info')" in tool and "entry(COMMON/'config')" in tool
