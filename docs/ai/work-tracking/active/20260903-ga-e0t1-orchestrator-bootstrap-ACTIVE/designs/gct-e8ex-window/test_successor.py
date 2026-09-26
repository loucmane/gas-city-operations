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
    """s1 r2 (B should_fix 3): gc runs under a read-only bind of / (so it cannot repair live runtime assets), with
    GIT_OPTIONAL_LOCKS=0. The network stays shared: the Bead store is the local Dolt server on 127.0.0.1."""
    run = subprocess.run(['/usr/bin/bwrap', '--ro-bind', '/', '/', '--new-session', '--die-with-parent', '--proc',
                          '/proc', '--dev', '/dev', '--', '/home/loucmane/gascity/bin/gc', '--city',
                          '/home/loucmane/gascity/city', '--rig', 'gas-city-template', 'bd', 'show', name, '--json'],
                         env=ENV, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    [row] = json.loads(run.stdout)
    return row, run.stdout


def template_git(g, *args):
    """The WORKTREE job's own pre-add form: -C the Template repository, hooks, fsmonitor and attributesFile off."""
    return subprocess.run(['/usr/bin/env', '-i', 'HOME=/nonexistent', 'USER=loucmane', 'LOGNAME=loucmane',
                           'LANG=C.UTF-8', 'PATH=/usr/bin:/bin', 'GIT_CONFIG_NOSYSTEM=1', 'GIT_CONFIG_GLOBAL=/dev/null',
                           'GIT_ATTR_NOSYSTEM=1', 'GIT_OPTIONAL_LOCKS=0', '/usr/bin/git', '--no-optional-locks', '-C',
                           g.TEMPLATE_REPO, '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-c',
                           'core.attributesFile=/dev/null', *args], capture_output=True, check=False).stdout


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
        # The package directory is gct-e8ex-window; gct-mbg6-window names only /var/tmp output roots.
        assert not re.search(r'(?<!/var/tmp/)gct-mbg6-window', text), name
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


def test_codex_cannot_write_the_template_git_metadata():
    """s1 r5 (operator decision 2026-09-26): the window's codex choice has exactly the vault and the Template
    worktrees as write roots, never the Template .git, from the pinned city.toml. The deployed default (which does
    list the .git) is what the overlay replaces."""
    base = load(HERE/'window-base-r11.py', 'window_base_codex_narrow')
    raw = Path('/home/loucmane/gascity/city/city.toml').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == base.CITY_SHA[0]
    city = tomllib.loads(raw.decode())
    [schema] = [o for o in city['providers']['codex']['options_schema'] if o.get('key') == 'worklog_access']
    [picked] = [c for c in schema['choices'] if c['value'] == 'classified-vault-and-template-worktrees']
    assert picked['flag_args'][:3] == ['--sandbox', 'workspace-write', '-c']
    roots = json.loads(picked['flag_args'][-1].split('=', 1)[1])
    assert roots == ['/home/loucmane/vaults/main/GasCity', '/home/loucmane/gas-city-template-worktrees']
    prep = (HERE/'prep-r11.py').read_text()
    assert "NARROW_ACCESS = 'classified-vault-and-template-worktrees'" in prep


def test_deployed_codex_default_still_lists_the_git():
    """The deployed default (the choice the overlay replaces) lists the Template .git, pinned by city.toml."""
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
             "'task id'", "'gc.work_dir'", "==DESCRIPTION_SHA,'description'", "'task has notes or an assignee before routing'",
             "'task view over the split cap'", "argv=w.GC+['--rig','gas-city-template','sling'"]
    positions = [route.index(token) for token in order]
    assert positions == sorted(positions)
    assert 'cg.no_drivers(' not in route and 'pr.check(' not in route


def test_template_drivers_are_the_pinned_lfs_set(g):
    """The live Template driver config and .gitattributes are exactly what WORKTREE (before the add, in this same
    form) and ROUTE pin; the tracked .gitattributes selects no filter, diff or merge driver."""
    drivers = template_git(g, 'config', '--includes', '--get-regexp', r'^(filter|diff|merge)\.')
    assert hashlib.sha256(drivers).hexdigest() == g.LFS_DRIVERS_SHA
    assert template_git(g, 'rev-parse', '--verify', g.BASE + ':.gitattributes').decode().strip() == g.GITATTRIBUTES_BLOB
    content = template_git(g, 'cat-file', 'blob', g.GITATTRIBUTES_BLOB)
    assert content == g.GITATTRIBUTES_BYTES
    rules = [line for line in content.decode().splitlines() if line and not line.startswith('#')]
    assert rules == ['patches/*.patch -whitespace']
    attrs = [p for p in template_git(g, 'ls-tree', '-r', '-z', '--name-only', '--full-tree', g.BASE).split(b'\0')
             if p.rsplit(b'/', 1)[-1] == b'.gitattributes']
    assert attrs == [b'.gitattributes']
    assert not os.path.lexists(g.TEMPLATE_REPO + '/.git/info/attributes')
    worktree = (HERE/'worktree-task-r1.py').read_text()
    assert worktree.index("'.gitattributes content'") < worktree.index("git('worktree','add'")
    assert worktree.index("'repository attributes file present'") < worktree.index("git('worktree','add'")


def test_wrappers_resolve_to_this_package():
    """s1 r2 (A and B must_fix 1): every wrapper's C= resolves to this directory, and HOLD's CONTAIN wrappers exist."""
    for wrapper in (HERE/'operator').glob('*.sh'):
        text = wrapper.read_text()
        [w] = re.findall(r'^W=(\S+)$', text, re.M)
        [d] = re.findall(r'^D=\$W/(\S+)$', text, re.M)
        [c] = re.findall(r'^C=\$D/(\S+)$', text, re.M)
        assert Path(w, d, c).resolve() == HERE.resolve(), wrapper.name
    hold = load(HERE/'hold-r11.py', 'hold_paths')
    for contain in hold.CONTAIN:
        assert contain.startswith('designs/%s/operator/' % HERE.name), contain
        assert (HERE.parent.parent/contain).is_file(), contain


def test_watch_runs_no_git_while_the_worker_is_live():
    """s1 r2 (B must_fix 2): the codex sandbox can write the Template .git, so WATCH never runs git."""
    watch = (HERE/'watch-r11.py').read_text()
    code = watch.split('"""', 2)[2]
    assert 'HARDENED' not in code and "'git-" not in code and '/usr/bin/git' not in code
    assert 'head = branch = None' in code
    assert 'note_markers=markers' in code and 'os.walk(evidence)' not in code


def test_watch_config_read_cannot_block(tmp_path):
    """s1 r4 (r3 review A must_fix 1): the WATCH config read, run on a planted FIFO, returns at once."""
    import threading
    watch = (HERE/'watch-r11.py').read_text()
    start = watch.index('    try:\n        fd = os.open(')
    end = watch.index("        template_config = 'unreadable: %s' % exc.__class__.__name__\n") + len(
        "        template_config = 'unreadable: %s' % exc.__class__.__name__\n")
    block = watch[start:end]
    assert 'os.O_NONBLOCK' in block and 'stat.S_ISREG(s.st_mode)' in block
    fifo = tmp_path/'config'
    os.mkfifo(fifo)
    code = 'import hashlib, os, stat\ndef read():\n' + block.replace("'/home/loucmane/gas-city-template/.git/config'",
                                                                   repr(str(fifo))) + '    return template_config\n'
    scope = {}
    exec(compile(code, 'watch-config-read', 'exec'), scope)
    result = []
    thread = threading.Thread(target=lambda: result.append(scope['read']()), daemon=True)
    thread.start()
    thread.join(5)
    assert result and result[0].startswith('not a plain file'), result


def test_common_snapshot_covers_the_whole_git_directory(g):
    """s1 r2 (B must_fix 3): every file and link under the Template .git but the object store and this index."""
    tool = load(HERE/'common-snapshot-r1.py', 'common_snapshot')
    assert tool.MUTABLE == {'worktrees/%s/index' % g.TASK}
    if not Path(g.ADMIN).exists():
        tool.BRANCH = 'HEAD'  # before WORKTREE the candidate branch does not exist; the walk is what is tested
    seen = tool.observe()
    control, objects = seen['control'], seen['objects']
    assert 'config' in control and 'HEAD' in control and seen['candidate_branch']
    assert any(k.startswith('refs/') for k in control) and any(k.startswith('logs/') for k in control)
    assert any(k.startswith('worktrees/') and k.endswith('/gitdir') for k in control)
    assert not any(k == 'objects' or k.startswith('objects/') for k in control)
    assert 'objects' in objects and 'objects/pack' in objects
    assert any(k.startswith('objects/pack/pack-') and k.endswith('.pack') for k in objects)
    assert ('packed-refs' in control) == os.path.exists(g.TEMPLATE_REPO + '/.git/packed-refs')
    assert 'subprocess' not in (HERE/'common-snapshot-r1.py').read_text()
    # The live baseline carries no non-sample hook, grafts, shallow, replace refs or alternates.
    assert tool.baseline_problems(seen) == []


def fake_git(tool, root, g):
    """A minimal common directory for the snapshot's behaviour: config, the candidate ref, a pack, a loose object,
    this worktree's index."""
    import zlib
    common = root/'.git'
    (common/'refs/heads/codex').mkdir(parents=True)
    (common/'config').write_text('[core]\n')
    (common/'HEAD').write_text('ref: refs/heads/main\n')
    (common/('refs/heads/' + g.BRANCH)).write_text(g.BASE + '\n')
    (common/'objects/pack').mkdir(parents=True)
    (common/('objects/pack/pack-%s.pack' % ('1' * 40))).write_bytes(b'PACK')
    (common/('worktrees/%s' % g.TASK)).mkdir(parents=True)
    (common/('worktrees/%s/index' % g.TASK)).write_bytes(b'DIRC')
    tool.COMMON = common
    return common, zlib


def loose(common, zlib, body, kind=b'blob'):
    raw = kind + b' %d\0' % len(body) + body
    name = hashlib.sha1(raw).hexdigest()
    (common/'objects'/name[:2]).mkdir(exist_ok=True)
    (common/'objects'/name[:2]/name[2:]).write_bytes(zlib.compress(raw))
    return common/'objects'/name[:2]/name[2:]


def test_common_snapshot_allows_only_git_add(g, tmp_path):
    """s1 r3 (reviews of 709fcb33, A must_fix 1, B must_fix 1-2): the after comparison, on a fake common directory.
    Allowed: new loose objects that hash to their name, and this worktree's index rewritten. Refused: an existing
    object overwritten, a new pack, a new loose object that does not hash to its name, a directory replaced by a
    link, a moved branch, a config write. An unlistable directory raises."""
    def fresh(name):
        tool = load(HERE/'common-snapshot-r1.py', 'common_snapshot_' + name)
        common, zlib = fake_git(tool, tmp_path/name, g)
        existing = loose(common, zlib, b'base content')
        return tool, common, zlib, existing, tool.observe()

    tool, common, zlib, existing, before = fresh('ok')
    loose(common, zlib, b'staged content')
    (common/('worktrees/%s/index' % g.TASK)).write_bytes(b'DIRC2')
    assert tool.compare(before, tool.observe()) == []

    tool, common, zlib, existing, before = fresh('overwrite')
    existing.write_bytes(zlib.compress(b'blob 4\0evil'))
    assert tool.compare(before, tool.observe()) != []

    tool, common, zlib, existing, before = fresh('pack')
    (common/('objects/pack/pack-%s.pack' % ('2' * 40))).write_bytes(b'PACK')
    assert tool.compare(before, tool.observe()) != []

    tool, common, zlib, existing, before = fresh('misnamed')
    (common/'objects/ee').mkdir()
    (common/'objects/ee'/('e' * 38)).write_bytes(zlib.compress(b'blob 3\0abc'))
    assert tool.compare(before, tool.observe()) != []

    tool, common, zlib, existing, before = fresh('link')
    (common/'objects/pack').rename(common/'objects/moved')
    (common/'objects/pack').symlink_to(common/'objects/moved')
    assert tool.compare(before, tool.observe()) != []

    tool, common, zlib, existing, before = fresh('branch')
    (common/('refs/heads/' + g.BRANCH)).write_text('0' * 40 + '\n')
    assert tool.compare(before, tool.observe()) != []

    tool, common, zlib, existing, before = fresh('config')
    (common/'config').write_text('[core]\n\tfsmonitor = /tmp/x\n')
    assert tool.compare(before, tool.observe()) == ['config']

    # s1 r4 (r3 review A should_fix 7): the remaining shapes.
    for name, shape in (('midx', 'objects/pack/multi-pack-index'), ('graph', 'objects/info/commit-graph'),
                        ('alternates', 'objects/info/alternates')):
        tool, common, zlib, existing, before = fresh(name)
        (common/shape).parent.mkdir(exist_ok=True)
        (common/shape).write_bytes(b'x')
        assert tool.compare(before, tool.observe()) != [], name

    tool, common, zlib, existing, before = fresh('hardlink')
    added = loose(common, zlib, b'linked content')
    os.link(added, common/'objects'/'extra')
    assert tool.compare(before, tool.observe()) != []

    tool, common, zlib, existing, before = fresh('trailing')
    added = loose(common, zlib, b'trailing content')
    added.chmod(0o644)
    added.write_bytes(added.read_bytes() + b'junk')
    assert tool.compare(before, tool.observe()) != []

    tool, common, zlib, existing, before = fresh('worldwritable')
    added = loose(common, zlib, b'writable content')
    added.chmod(0o646)
    assert tool.compare(before, tool.observe()) != []

    for name in ('indexlink', 'indexhard'):
        tool, common, zlib, existing, before = fresh(name)
        index = common/('worktrees/%s/index' % g.TASK)
        index.rename(common/'moved-index')
        if name == 'indexlink':
            index.symlink_to(common/'moved-index')
        else:
            os.link(common/'moved-index', index)
        assert 'mutable-index' in tool.compare(before, tool.observe()), name

    tool, common, zlib, existing, before = fresh('packed')
    ref = common/('refs/heads/' + g.BRANCH)
    ref.unlink()
    (common/'packed-refs').write_text('# pack-refs with: peeled\n%s refs/heads/%s\n' % (g.BASE, g.BRANCH))
    assert tool.branch_target() == g.BASE

    # s1 r5: a replace ref in packed-refs fails the baseline; an addition in another group refuses.
    tool, common, zlib, existing, before = fresh('packedreplace')
    (common/'packed-refs').write_text('%s refs/replace/%s\n' % (g.BASE, g.BASE))
    assert any(p.startswith('packed-refs: refs/replace/') for p in tool.baseline_problems(tool.observe()))
    other = [gid for gid in os.getgroups() if gid != 1000]
    if other:
        tool, common, zlib, existing, before = fresh('group')
        added = loose(common, zlib, b'other group')
        os.chown(added, -1, other[0])
        assert str(added.relative_to(common)) in tool.compare(before, tool.observe())

    tool, common, zlib, existing, before = fresh('root')
    common.chmod(0o777)
    try:
        assert '.' in tool.compare(before, tool.observe())
    finally:
        common.chmod(0o755)

    # r3 review B should_fix 3: the full main() round trip, a removed object, a new control file, a linked loose.
    tool, common, zlib, existing, before = fresh('main')
    record = tmp_path/'main-before.json'
    assert tool.main(['before', str(record)]) == 0
    digest = hashlib.sha256(record.read_bytes()).hexdigest()
    loose(common, zlib, b'main staged')
    assert tool.main(['after', str(record), digest, str(tmp_path/'main-after-ok.json')]) == 0
    (common/'hooks').mkdir()
    (common/'hooks/pre-commit').write_text('#!/bin/sh\n')
    assert tool.main(['after', str(record), digest, str(tmp_path/'main-after-hook.json')]) == 1
    with pytest.raises(AssertionError):
        tool.main(['after', str(record), '0' * 64, str(tmp_path/'main-after-digest.json')])
    with pytest.raises(AssertionError):
        tool.main(['before', str(tmp_path/'main-before-hook.json')])

    tool, common, zlib, existing, before = fresh('removed')
    existing.unlink()
    assert tool.compare(before, tool.observe()) != []

    tool, common, zlib, existing, before = fresh('linkedloose')
    target = loose(common, zlib, b'real target')
    raw = target.read_bytes()
    target.unlink()
    (tmp_path/'outside').write_bytes(raw)
    target.symlink_to(tmp_path/'outside')
    assert tool.compare(before, tool.observe()) != []

    tool, common, zlib, existing, before = fresh('hidden')
    (common/'objects/info').mkdir()
    (common/'objects/info').chmod(0o311)
    try:
        with pytest.raises(PermissionError):
            tool.observe()
    finally:
        (common/'objects/info').chmod(0o755)


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
        suspended=False, work_dir=g.WORK, min_active_sessions=0, max_active_sessions=1,
        option_defaults=dict(worklog_access='classified-vault-and-template-worktrees'))]
    # s1 r5: the overlay the window installs gives codex the narrower choice, as Core itself resolves it.
    parsed = tomllib.loads(candidate.decode())
    [codex] = [a for a in parsed['patches']['agent'] if a.get('dir') == 'gas-city-template' and a.get('name') == 'codex'
               and 'work_dir' in a]
    assert codex['option_defaults'] == {'worklog_access': 'classified-vault-and-template-worktrees'}
    expected = prep.expected_config(baseline, selected, target, names)
    assert expected['config']['Agents'][target]['OptionDefaults'] == {
        'worklog_access': 'classified-vault-and-template-worktrees'}


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
    assert 'for directory,dirs,files in os.walk(COMMON,onerror=refuse):' in tool
