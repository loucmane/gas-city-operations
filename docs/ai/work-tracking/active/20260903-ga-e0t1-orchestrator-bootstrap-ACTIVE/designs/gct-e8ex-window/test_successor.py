"""Tests for the gct-mbg6 (gct-e8ex) twelfth-successor window package, the first Template codex window.

  python3 -m pytest -q designs/gct-e8ex-window/test_successor.py

Read-only: the package, the generator and its source commit, the pinned live files and build roots, one confined
`gc config show` / `gc order list` and `gc bd show` reads (all with GIT_OPTIONAL_LOCKS=0) and git reads of the
Template repository with no optional locks.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import tomllib
import types

import pytest

HERE = Path(__file__).parent
GEN = HERE/'generators'/'make_successor.py'
SPLIT = HERE.parent/'gct-e8ex-split'/'split_e8ex.py'
ENV = dict(HOME='/home/loucmane', USER='loucmane', LOGNAME='loucmane', LANG='C.UTF-8', GIT_OPTIONAL_LOCKS='0',
           GC_HOME='/home/loucmane/gascity/home', PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin')
CACHE_KEY = '954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/.git'
RECEIPT = '/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json'
HARDENED = ['/usr/bin/env', '-i', 'GIT_CONFIG_NOSYSTEM=1', 'GIT_CONFIG_GLOBAL=/dev/null', 'GIT_ATTR_NOSYSTEM=1',
            'HOME=/nonexistent', 'PATH=/usr/bin:/bin', '/usr/bin/git', '--no-optional-locks']


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
    run = subprocess.run(['/home/loucmane/gascity/bin/gc', '--city', '/home/loucmane/gascity/city', '--rig',
                          'gas-city-template', 'bd', 'show', name, '--json'], env=ENV, capture_output=True, text=True,
                         timeout=60)
    assert run.returncode == 0, run.stderr
    [row] = json.loads(run.stdout)
    return row, run.stdout


def template_git(g, *args):
    return subprocess.run(HARDENED + ['-C', g.TEMPLATE_REPO, *args], capture_output=True, check=True).stdout


def test_package_is_the_generator_output(generated):
    assert package_files() == generated


def test_scripts_compile_and_shell_parses():
    for path in HERE.glob('*.py'):
        compile(path.read_bytes(), str(path), 'exec', dont_inherit=True)
    for path in (HERE/'operator').glob('*.sh'):
        assert subprocess.run(['/bin/sh', '-n', str(path)]).returncode == 0, path
        assert os.stat(path).st_mode & 0o111, path


def test_no_leftovers():
    """No Operations-candidate identity survives outside the named history lines."""
    for name, raw in package_files().items():
        text = raw.decode()
        for token in ('gas-city-ops-candidate-worktrees', 'gas-city-ops/.git', 'codex/ga-3oa7', 'ga-elig', 'ga-aju4',
                      'EXCLUDE_AFTER', "'gc.check_path':CHECK", 'implementation-worker', 'SIGNING-RELEASE',
                      'exclude-task-r1.py', 'gct-TASK', 'TBD'):
            assert token not in text, (name, token)
        for line in text.splitlines():
            if 'operations-candidate-worker' in line:
                assert name == 'prep-r11.py' and 'provider claude-candidate' in line, (name, line)
            if re.search(r"'--rig', ?'gascity'", line) or re.search(r"\['rig', ?'(suspend|resume)', ?'gascity'", line):
                raise AssertionError((name, line))
            if 'ga-3oa7' in line:
                assert name in ('window-base-r11.py', 'prep-r11.py', 'bind-task-r5.py', 'observe-integrity-r11.py'), \
                    (name, line)


def test_every_output_root_is_fresh():
    roots = set()
    for name, raw in package_files().items():
        roots |= set(re.findall(r"/var/tmp/gct-mbg6-[A-Za-z0-9%<>_-]*?-(\d{8})-r\d", raw.decode()))
    assert roots == {'20260926'}, roots
    for name, raw in package_files().items():
        for root in re.findall(r"/var/tmp/ga-3oa7-[A-Za-z0-9_-]+", raw.decode()):
            assert root == '/var/tmp/ga-3oa7-terminal-20260926-r1', (name, root)


def test_wrappers_bind_their_scripts():
    for wrapper in (HERE/'operator').glob('*.sh'):
        text = wrapper.read_text()
        for script in re.findall(r'"\$C/([a-z0-9-]+\.py)" "\$([A-Z_]+)"', text):
            name, var = script
            [value] = re.findall(r'^%s=([0-9a-f]{64})$' % var, text, re.M)
            assert value == sha(HERE/name), (wrapper.name, name)


def test_identity(g):
    base = (HERE/'window-base-r11.py').read_text()
    assert "WORK = Path('/home/loucmane/gas-city-template-worktrees/gct-mbg6')" in base
    assert "BASE = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'" in base
    assert "ADMIN = Path('/home/loucmane/gas-city-template/.git/worktrees/gct-mbg6')" in base
    route = (HERE/'route-task-r5.py').read_text()
    assert "argv=w.GC+['--rig','gas-city-template','sling',TARGET,'gct-mbg6','--no-formula','--no-convoy','--json']" in route
    assert "TARGET='gas-city-template/codex'" in route
    lineage = (HERE/'suspension-lineage.py').read_text()
    assert "GC+['rig','resume','gas-city-template','--json']" in lineage
    worktree = (HERE/'worktree-task-r1.py').read_text()
    assert "BRANCH='codex/gct-mbg6-template-candidate-lane'" in worktree
    assert "OPS=Path('/home/loucmane/gas-city-template')" in worktree


def test_accepted_image_is_the_3oa7_terminal_record(g):
    base = (HERE/'window-base-r11.py').read_text()
    assert "ACCEPTED = Path('%s')\nACCEPTED_SHA = '%s'\n" % g.ACCEPTED_NEW in base
    assert "PROVIDER = Path('%s')\nPROVIDER_SHA = '%s'\n" % g.PROVIDER in base
    assert sha(g.ACCEPTED_NEW[0]) == g.ACCEPTED_NEW[1] and sha(g.PROVIDER[0]) == g.PROVIDER[1]
    entry = json.loads(Path(g.ACCEPTED_NEW[0]).read_bytes())['cache']['inventory'][CACHE_KEY]
    assert entry['mtime_ns'] == entry['ctime_ns'] == g.CACHE_PREV_NS
    result = json.loads(Path('/var/tmp/ga-3oa7-terminal-20260926-r1/result.json').read_bytes())
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


def test_live_pins():
    base = load(HERE/'window-base-r11.py', 'window_base_live')
    assert sha(base.WITNESS) == base.WITNESS_SHA
    assert sha(RECEIPT) == base.RECEIPT_SHA[0]
    assert sha('/home/loucmane/gascity/city/city.toml') == base.CITY_SHA[0]


def test_codex_can_write_the_template_git_metadata():
    """The composed codex session's sandbox write roots include the Template .git (git add, write-tree), from the
    pinned city.toml: the agent's worklog_access default selects the choice that lists it."""
    base = load(HERE/'window-base-r11.py', 'window_base_codex')
    raw = Path('/home/loucmane/gascity/city/city.toml').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == base.CITY_SHA[0]
    city = tomllib.loads(raw.decode())
    [codex] = [a for a in city['patches']['agent'] if a.get('dir') == 'gas-city-template' and a.get('name') == 'codex']
    choice = codex['option_defaults']['worklog_access']
    assert choice == 'classified-vault-template-worktrees-and-git-metadata'
    [schema] = [o for o in city['providers']['codex']['options_schema'] if o.get('key') == 'worklog_access']
    [picked] = [c for c in schema['choices'] if c['value'] == choice]
    roots = json.loads(picked['flag_args'][-1].split('=', 1)[1])
    assert roots == ['/home/loucmane/vaults/main/GasCity', '/home/loucmane/gas-city-template-worktrees',
                     '/home/loucmane/gas-city-template/.git']


def test_route_calls_the_reviewed_pieces_in_order():
    route = (HERE/'route-task-r5.py').read_text()
    for var in ('PREROUTE', 'CANDIDATE_GIT', 'RECORD'):
        [path] = re.findall(r"^%s=Path\('([^']+)'\)$" % var, route, re.M)
        [digest] = re.findall(r"^%s_SHA='([0-9a-f]{64})'$" % var, route, re.M)
        assert sha(path) == digest, var
    order = ['preroute-bead', 'pr.city_problems(', 'cg.verify_linked(', 'cg.no_gitlinks(',
             "'Template driver config is not the git-lfs set'", "'routed worktree is not freshly clean'", 'pr.survey(',
             "'gc.work_dir'", "==DESCRIPTION_SHA,'description'", "'task has notes or an assignee before routing'",
             "'task view over the split cap'", "argv=w.GC+['--rig','gas-city-template','sling'"]
    positions = [route.index(token) for token in order]
    assert positions == sorted(positions)
    assert 'cg.no_drivers(' not in route and 'pr.check(' not in route


def test_template_drivers_are_the_pinned_lfs_set(g):
    """The live Template driver config and .gitattributes are exactly what WORKTREE and ROUTE pin."""
    drivers = subprocess.run(HARDENED + ['--git-dir=' + g.TEMPLATE_REPO + '/.git', 'config', '--includes',
                                         '--get-regexp', r'^(filter|diff|merge)\.'], capture_output=True).stdout
    assert hashlib.sha256(drivers).hexdigest() == g.LFS_DRIVERS_SHA
    assert template_git(g, 'rev-parse', '--verify', g.BASE + ':.gitattributes').decode().strip() == g.GITATTRIBUTES_BLOB
    attrs = [p for p in template_git(g, 'ls-tree', '-r', '-z', '--name-only', '--full-tree', g.BASE).split(b'\0')
             if p.rsplit(b'/', 1)[-1] == b'.gitattributes']
    assert attrs == [b'.gitattributes']
    assert not os.path.lexists(g.TEMPLATE_REPO + '/.git/info/attributes')


def test_bind_writes_only_the_work_dir(g):
    bind = (HERE/'bind-task-r5.py').read_text()
    code = bind.split('"""', 2)[2]
    assert "metadata={'gc.work_dir':WORK}" in bind and 'gc.check_path' not in code
    assert 'opt_' not in code and 'template_overrides' not in code and '--append-notes' not in code
    assert "assert not before.get('notes'),'task has notes before the first session'" in bind
    assert "DESCRIPTION_SHA='%s'" % g.DESCRIPTION_SHA in bind
    route = (HERE/'route-task-r5.py').read_text()
    assert "DESCRIPTION_SHA='%s'" % g.DESCRIPTION_SHA in route and "BIND_SHA='%s'" % sha(HERE/'bind-task-r5.py') in route


def test_brief_is_the_reviewed_split(g):
    """The live task and holders are the reviewed split render for these ids."""
    split = load(SPLIT, 'split_e8ex')
    task, raw = bead(g.TASK)
    assert task['description'] == split.task(g.HOLDERS, g.TASK)
    assert hashlib.sha256(task['description'].encode()).hexdigest() == g.DESCRIPTION_SHA
    assert task['status'] == 'open' and not task.get('dependencies') and not task.get('notes')
    if not task.get('metadata'):
        assert not task.get('assignee')
    texts = split.holders(g.TASK)
    for n, name in enumerate(g.HOLDERS, 1):
        holder, _ = bead(name)
        assert holder['status'] == 'closed' and not holder.get('dependencies') and not holder.get('dependents'), name
        assert holder['description'] == texts['spec-%d.md' % n], name


def test_worktree_preconditions(g):
    assert template_git(g, 'rev-parse', '--verify', 'refs/remotes/origin/main^{commit}').decode().strip() == g.BASE
    if Path(g.WORK).exists():
        pytest.skip('WORKTREE has run')
    assert not Path(g.ADMIN).exists()
    assert subprocess.run(HARDENED + ['-C', g.TEMPLATE_REPO, 'rev-parse', '--verify', '--quiet',
                                      'refs/heads/' + g.BRANCH], capture_output=True).returncode == 1


def test_overlay_recomputes(g):
    prep = load(HERE/'prep-r11.py', 'prep')
    city = prep.read(prep.CITY/'city.toml', prep.CITY_SHA)
    baseline = prep.config()
    orders = prep.confined([str(prep.GC), '--city', str(prep.CITY), 'order', 'list', '--json'])
    candidate, patches, names, target, selected = prep.build_overlay(city, baseline, orders)
    assert hashlib.sha256(candidate).hexdigest() == g.OVERLAY_NEW == prep.OVERLAY_SHA
    assert [p for p in patches if not p['suspended']] == [dict(dir='gas-city-template', name='codex',
        suspended=False, work_dir=g.WORK, min_active_sessions=0, max_active_sessions=1)]


PREP_ROOT = Path('/var/tmp/gct-mbg6-prep-20260926-r1')


def test_prep_outputs_are_pinned(g):
    if g.CACHE_PINNED_NS is None:
        pytest.skip('s1: PREP not yet pinned')
    base = (HERE/'window-base-r11.py').read_text()
    result = json.loads((PREP_ROOT/'result.json').read_bytes())
    assert result['ok'] is True and result['installed'] is False and result['worker_launched'] is False
    assert result['changed_receipt_fields'] == ['permission_revision', 'receipt_sha256']
    for value in (sha(PREP_ROOT/'city.isolated.toml'), sha(PREP_ROOT/'receipt.final.json'), result['revision_after'],
                  sha(PREP_ROOT/'result.json'), sha(PREP_ROOT/'orders.isolated.json')):
        assert "'%s'" % value in base, value
    assert result['city_after_sha256'] == sha(PREP_ROOT/'city.isolated.toml') == g.OVERLAY_NEW


def test_window_base_pins_run_against_the_live_prep(g):
    if g.CACHE_PINNED_NS is None or not PREP_ROOT.exists():
        pytest.skip('s1: PREP not yet pinned')
    load(HERE/'window-base-r11.py', 'window_base_pins').pins()


def test_cache_value_is_pinned_to_the_live_value(g):
    if g.CACHE_PINNED_NS is None:
        pytest.skip('s1: the cache value is pinned at s2')
    live = os.lstat('/home/loucmane/gascity/home/cache/repos/' + CACHE_KEY)
    assert live.st_mtime_ns == live.st_ctime_ns == g.CACHE_PINNED_NS


def test_common_snapshot_covers_the_template_git(g):
    tool = (HERE/'common-snapshot-r1.py').read_text()
    assert "COMMON=Path('/home/loucmane/gas-city-template/.git')" in tool
    assert "BASE='%s'" % g.BASE in tool and "BRANCH='refs/heads/%s'" % g.BRANCH in tool
    assert "for sub in ('hooks','info')" in tool and "entry(COMMON/'config')" in tool
