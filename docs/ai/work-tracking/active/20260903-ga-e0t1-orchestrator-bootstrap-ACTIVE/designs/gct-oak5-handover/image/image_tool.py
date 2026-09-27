"""gct-oak5 handover image tool r2 (plan r18, "Handover images and the route gate").

  image_tool.py export  --worktree W --clone C --base B --out O --runtime none|claude|claude,codex [--codex-hooks-sha S]
  image_tool.py compare --step C1|X|C2 --prev P.json --next N.json
  image_tool.py verify  --image I.json --copy D --clone C
  image_tool.py holder  --image I.json --step C1|X

export reads the handover worktree with no git anywhere under it (the gct-mbg6 intake method): it walks
directory descriptors without following links, compares every entry with the BASE tree read from a bare
GitHub clone, then walks again and requires the same paths and stat data (no change while reading). Ignored
status comes from BASE's .gitignore files in a scratch mirror. It writes <out>/image.json:
- entries: every modified (M) or added (A) path, with git mode, blob id, sha256 and size;
- deleted: tracked paths that are missing;
- ignored: every ignored entry that is not RUNTIME, with mode, size and sha256 (links, hard links and special
  files among them refuse);
- runtime: every RUNTIME entry, checked against the digest-pinned pins.json for the lanes named by --runtime,
  and the RUNTIME directory modes;
- skill_targets: a digest of every pinned skill target tree, so SKILL.md content cannot change unseen;
- git: the worktree .git gitfile (exactly the canonical admin path), the admin HEAD, gitdir, commondir and
  config.worktree, the branch ref (which must equal BASE) and the canonical HEAD, all read as files.
It refuses a nested `.git` path component (any case), a stop path added, changed or deleted, a leftover
`.oak5-c2-tmp`, output under a forbidden root and any input over the bounds. Every error is a refusal (rc 2).

compare implements route-gate rules 2 to 4 for one step: the step's lanes and exact contract (C1: image 0 is
empty and image 1 holds exactly {M1 M, A1 A}; X: image 2 holds exactly image 1's paths unchanged plus
{M2 M, A2 A}; C2: the final export holds exactly the four contract paths with their statuses), no
agent-control path, no ignored entry, RUNTIME entries unchanged across images (`.gc/settings.json` is pinned
per image to the live city file instead), skill targets and git metadata unchanged.

verify is the tamper negative: it exports the content of a copy of the worktree (no git metadata) with the
image's lanes and requires every content field to equal the image (the copy's own path is normalised).

holder prints the DIGEST lines of the step's contract paths from an image, for the image holder.

Limits: empty directories outside RUNTIME, file modes other than git's 100644/100755 for contract entries, and
group or other mode bits are not recorded.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys

SCHEMA = 'gct-oak5.handover-image.v2'
HERE = Path(__file__).resolve().parent
PINS_SHA256 = '84b0180f019bbf1441941308c7a299f53c38a311fd5e5620122fd9f51466158f'
WORKTREE = '/home/loucmane/gas-city-template-candidate-worktrees/gct-oak5'
CANONICAL_GIT = Path('/home/loucmane/gas-city-template/.git')
BRANCH = 'codex/gct-oak5-handover-proof'
FORBIDDEN_ROOTS = (Path('/home/loucmane/vaults/main/GasCity'), Path('/home/loucmane/gas-city-template-worktrees'),
                   Path('/home/loucmane/gas-city-template-candidate-worktrees'), Path('/home/loucmane/gas-city-template'),
                   Path('/home/loucmane/.local/share/gas-city-staging/gct-oak5-handover/probe-target'),
                   Path('/tmp'), Path('/var/tmp'), Path('/dev/shm'))
STOP_NAMES = ('.gitignore', '.gitattributes', '.gitmodules', '.lfsconfig')
CONTROL_DIRS = ('.codex', '.agents', '.claude', '.gc')
CONTROL_NAMES_PREFIX = ('AGENTS', 'CLAUDE')
CONTROL_NAMES = ('.mcp.json', 'conftest.py', 'sitecustomize.py')
C2_TMP = '.oak5-c2-tmp'
MAX_WALK = 20000
MAX_DEPTH = 40
MAX_FILES = 1000
MAX_FILE_BYTES = 8 << 20
MAX_TOTAL_BYTES = 32 << 20
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOATIME
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK | os.O_NOATIME
CITY_FILES = {'.gc/settings.json': ('/home/loucmane/gascity/city/.gc/settings.json', 0o644),
              '.gc/scripts/mol-dog-stale-db.sh': ('/home/loucmane/gascity/city/.gc/scripts/mol-dog-stale-db.sh', 0o755)}
PER_IMAGE = ('.gc/settings.json',)
LANES = {
    'claude': {'sink': '.claude/skills', 'catalog': '.gc/tmp/skill-catalog-gas-city-template_gc.implementation-worker.b64'},
    'codex': {'sink': '.agents/skills', 'catalog': '.gc/tmp/skill-catalog-gas-city-template_codex.b64'},
}
BASE_DIR_MODES = {'.gc': 0o700, '.gc/tmp': 0o700, '.gc/scripts': 0o755}
LANE_DIR_MODES = {'claude': {'.claude/skills': 0o755},
                  'codex': {'.agents': 0o755, '.agents/skills': 0o755, '.codex': 0o755}}
STEPS = {
    'C1': dict(prev=[], next=['claude'], contract={'docs/native-findings.md': 'M', 'lib/gct_handover_digest.py': 'A'},
               carry=()),
    'X': dict(prev=['claude'], next=['claude', 'codex'],
              contract={'docs/bead-conventions.md': 'M', 'tests/test_gct_handover_digest.py': 'A'},
              carry=('docs/native-findings.md', 'lib/gct_handover_digest.py')),
    'C2': dict(prev=['claude', 'codex'], next=['claude', 'codex'],
               contract={'docs/native-findings.md': 'M', 'lib/gct_handover_digest.py': 'A',
                         'docs/bead-conventions.md': 'M', 'tests/test_gct_handover_digest.py': 'A'}, carry=()),
}
_PINS = None


class Refusal(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise Refusal(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def blob_id(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def pins():
    global _PINS
    if _PINS is None:
        raw = (HERE / 'pins.json').read_bytes()
        require(sha256(raw) == PINS_SHA256, 'pins.json digest differs from the pinned digest')
        _PINS = json.loads(raw)
    return _PINS


def ownership_bytes():
    return json.dumps({'targets': pins()['skill_map']}, separators=(',', ':'), sort_keys=True).encode()


def git(repo, *args, stdin=None):
    base = ['/usr/bin/git', '--no-optional-locks', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
            '-c', 'core.attributesFile=/dev/null', '-c', 'core.excludesFile=/dev/null', '--git-dir', str(repo)]
    environment = dict(HOME='/nonexistent', PATH='/usr/bin:/bin', LANG='C.UTF-8', GIT_CONFIG_NOSYSTEM='1',
                       GIT_CONFIG_GLOBAL='/dev/null', GIT_ATTR_NOSYSTEM='1', GIT_NO_REPLACE_OBJECTS='1',
                       GIT_TERMINAL_PROMPT='0')
    r = subprocess.run(base + list(args), input=stdin, capture_output=True, env=environment, timeout=300)
    require(r.returncode == 0, 'git %s: %s' % (args[0], r.stderr.decode(errors='replace')[-400:]))
    return r.stdout


def outside(path):
    real = Path(os.path.realpath(path))
    for root in FORBIDDEN_ROOTS:
        require(real != root and root not in real.parents, 'path under a forbidden root: ' + str(path))
    return real


def check_clone(clone, base):
    clone = outside(clone)
    require(not (clone / 'objects/info/alternates').exists(), 'clone has alternates')
    replace = clone / 'refs/replace'
    require(not replace.exists() or not any(replace.rglob('*')), 'clone has replace refs')
    require(git(clone, 'rev-parse', '--verify', base + '^{commit}').decode().strip() == base, 'BASE missing')
    return clone


def base_tree(clone, base):
    tree = {}
    for row in git(clone, 'ls-tree', '-r', '-z', '--full-tree', base).split(b'\0'):
        if not row:
            continue
        meta, path = row.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        require(mode != '160000', 'BASE has a gitlink')
        tree[path.decode()] = (mode, oid)
    return tree


def walk(root):
    """({path: lstat}, {dir: lstat}) for everything under root, by descriptor, never following a link."""
    entries, dirs = {}, {}

    def visit(fd, rel, depth):
        require(depth <= MAX_DEPTH, 'directory depth over the bound at ' + rel)
        for name in sorted(os.listdir(fd)):
            path = rel + '/' + name if rel else name
            path.encode('utf-8')
            s = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(len(entries) + len(dirs) < MAX_WALK, 'walk over the bound')
            if not rel and name == '.git':
                require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'worktree .git is not a single-link gitfile')
                continue
            require(name.lower() != '.git', 'nested .git component: ' + path)
            if stat.S_ISDIR(s.st_mode):
                dirs[path] = s
                sub = os.open(name, DIR_FLAGS, dir_fd=fd)
                try:
                    visit(sub, path, depth + 1)
                finally:
                    os.close(sub)
            else:
                entries[path] = s
    fd = os.open(root, DIR_FLAGS)
    try:
        visit(fd, '', 0)
        return entries, dirs
    finally:
        os.close(fd)


def stat_key(s):
    return (s.st_mode, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink, s.st_uid)


def open_parent(root, path):
    parts = PurePosixPath(path).parts
    fd = os.open(root, DIR_FLAGS)
    for part in parts[:-1]:
        nxt = os.open(part, DIR_FLAGS, dir_fd=fd)
        os.close(fd)
        fd = nxt
    return fd, parts[-1]


def read_regular(root, path, lstat_before=None):
    """(fstat, bytes) of a single-link regular file, opened component by component with O_NOFOLLOW."""
    fd, name = open_parent(root, path)
    try:
        f = os.open(name, FILE_FLAGS, dir_fd=fd)
        try:
            s = os.fstat(f)
            require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'not a single-link regular file: ' + path)
            require(s.st_size <= MAX_FILE_BYTES, 'file over the bound: ' + path)
            if lstat_before is not None:
                require(stat_key(s) == stat_key(lstat_before), 'file changed after the walk: ' + path)
            chunks = []
            while True:
                chunk = os.read(f, 1 << 20)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b''.join(chunks)
            require(len(data) == s.st_size and stat_key(os.fstat(f)) == stat_key(s), 'file changed while read: ' + path)
            return s, data
        finally:
            os.close(f)
    finally:
        os.close(fd)


def readlink_at(root, path):
    fd, name = open_parent(root, path)
    try:
        return os.readlink(name, dir_fd=fd)
    finally:
        os.close(fd)


def read_file(path):
    """(fstat, bytes) of a single-link regular file outside the worktree (git metadata, city files)."""
    f = os.open(path, FILE_FLAGS)
    try:
        s = os.fstat(f)
        require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'not a single-link regular file: ' + str(path))
        require(s.st_size <= MAX_FILE_BYTES, 'file over the bound: ' + str(path))
        data = b''
        while chunk := os.read(f, 1 << 20):
            data += chunk
        return s, data
    finally:
        os.close(f)


def ignored(clone, tree, dirs, paths, scratch):
    """BASE's .gitignore rules applied to paths, in a mirror holding only those files and the directory skeleton."""
    if not paths:
        return set()
    mirror = scratch / 'mirror'
    mirror.mkdir(mode=0o700)
    try:
        for d in sorted(dirs):
            (mirror / d).mkdir(mode=0o700, exist_ok=True)
        for path, (mode, oid) in tree.items():
            if PurePosixPath(path).name == '.gitignore':
                target = mirror / path
                require(not target.exists() or target.is_file(), 'tracked .gitignore replaced by a directory: ' + path)
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                target.write_bytes(git(clone, 'cat-file', 'blob', oid))
        r = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-c', 'core.hooksPath=/dev/null', '-c',
                            'core.fsmonitor=false', '-c', 'core.excludesFile=/dev/null', '--git-dir', str(clone),
                            '--work-tree', str(mirror), 'check-ignore', '--no-index', '-z', '--stdin'],
                           input=b'\0'.join(p.encode() for p in paths) + b'\0', capture_output=True, timeout=300,
                           env=dict(HOME='/nonexistent', PATH='/usr/bin:/bin', GIT_CONFIG_NOSYSTEM='1',
                                    GIT_CONFIG_GLOBAL='/dev/null', GIT_NO_REPLACE_OBJECTS='1'))
        require(r.returncode in (0, 1), 'check-ignore: ' + r.stderr.decode(errors='replace')[-300:])
        return {p.decode() for p in r.stdout.split(b'\0') if p}
    finally:
        shutil.rmtree(mirror)


def expected_runtime(lanes, codex_hooks_sha):
    """{path: spec} for every RUNTIME entry the named lanes write, from worker-independent pins."""
    expected = {}
    if not lanes:
        return expected
    for path, (source, mode) in CITY_FILES.items():
        _, data = read_file(source)
        expected[path] = dict(kind='file', mode=mode, sha256=sha256(data))
    for lane in lanes:
        sink = LANES[lane]['sink']
        expected[sink + '/.gc-skill-ownership.json'] = dict(kind='file', mode=0o644, sha256=sha256(ownership_bytes()))
        for name, target in pins()['skill_map'].items():
            expected[sink + '/' + name] = dict(kind='link', target=target)
        expected[LANES[lane]['catalog']] = dict(kind='catalog', mode=0o600)
    if 'codex' in lanes:
        require(bool(codex_hooks_sha), '--codex-hooks-sha is required for the codex lane')
        expected['.codex/hooks.json'] = dict(kind='file', mode=0o644, sha256=codex_hooks_sha)
    return expected


def tree_digest(root):
    """sha256 over every regular file under a skill target (sorted relative path and bytes); links refuse."""
    h = hashlib.sha256()
    entries, dirs = walk(root)
    for path in sorted(entries):
        s = entries[path]
        require(stat.S_ISREG(s.st_mode), 'skill target holds a non-regular entry: %s/%s' % (root, path))
        h.update(path.encode() + b'\0' + read_regular(root, path)[1] + b'\0')
    return h.hexdigest()


def skill_targets():
    digests = {}
    for name, target in sorted(pins()['skill_map'].items()):
        require(os.path.realpath(target) == target and '/../' not in target and '/./' not in target,
                'skill target is not a clean real path: ' + target)
        s = os.lstat(target)
        require(stat.S_ISDIR(s.st_mode) and s.st_uid == os.getuid(), 'skill target is not an operator directory: ' + target)
        require(stat.S_ISREG(os.lstat(target + '/SKILL.md').st_mode), 'skill target has no SKILL.md: ' + target)
        digests[name] = tree_digest(target)
    return digests


def catalog_ok(data):
    try:
        value = json.loads(base64.b64decode(data, validate=True))
    except (ValueError, TypeError):
        return False
    return value == pins()['catalog_value']


def content(worktree, clone, base, lanes, codex_hooks_sha):
    """The content part of an image: entries, deleted, ignored, runtime, runtime dir modes."""
    check_clone(clone, base)
    tree = base_tree(clone, base)
    found, dirs = walk(worktree)
    require(not [d for d in dirs if PurePosixPath(d).name == C2_TMP] and C2_TMP not in found,
            C2_TMP + ' is present')
    scratch = Path(os.path.realpath(clone)).parent / (Path(clone).name + '.scratch')
    outside(scratch)
    require(not scratch.exists(), 'scratch exists: ' + str(scratch))
    scratch.mkdir(mode=0o700)
    try:
        ignore = ignored(clone, tree, dirs, [p for p in sorted(found) if p not in tree], scratch)
    finally:
        scratch.rmdir()

    expected = expected_runtime(lanes, codex_hooks_sha)
    runtime, entries, ignored_entries, total = [], [], [], 0
    for path in sorted(found):
        s = found[path]
        name = PurePosixPath(path).name
        if path in tree:
            mode, oid = tree[path]
            if mode == '120000':
                require(stat.S_ISLNK(s.st_mode) and blob_id(readlink_at(worktree, path).encode()) == oid,
                        'tracked link changed: ' + path)
                continue
            require(stat.S_ISREG(s.st_mode), 'tracked file is not a regular file: ' + path)
            st, data = read_regular(worktree, path, s)
            now = '100755' if st.st_mode & stat.S_IXUSR else '100644'
            if blob_id(data) == oid and now == mode:
                continue
            require(name not in STOP_NAMES, 'stop path changed: ' + path)
            entries.append(dict(path=path, status='M', mode=now, blob=blob_id(data), sha256=sha256(data), size=len(data)))
            total += len(data)
            continue
        require(name not in STOP_NAMES, 'stop path added: ' + path)
        if path in expected:
            spec = expected[path]
            if spec['kind'] == 'link':
                require(stat.S_ISLNK(s.st_mode) and readlink_at(worktree, path) == spec['target'],
                        'runtime link differs: ' + path)
                runtime.append(dict(path=path, kind='link', target=spec['target']))
            else:
                require(stat.S_ISREG(s.st_mode), 'runtime entry is not a regular file: ' + path)
                st, data = read_regular(worktree, path, s)
                require(stat.S_IMODE(st.st_mode) == spec['mode'] and st.st_uid == os.getuid(), 'runtime mode: ' + path)
                if spec['kind'] == 'catalog':
                    require(catalog_ok(data), 'runtime catalog differs: ' + path)
                else:
                    require(sha256(data) == spec['sha256'], 'runtime bytes differ: ' + path)
                runtime.append(dict(path=path, kind=spec['kind'], mode=oct(spec['mode']), sha256=sha256(data)))
            continue
        require(not path.startswith(tuple(d + '/' for d in CONTROL_DIRS)),
                'unadmitted control-namespace entry: ' + path)
        if path in ignore:
            require(stat.S_ISREG(s.st_mode), 'ignored entry is not a regular file: ' + path)
            st, data = read_regular(worktree, path, s)
            ignored_entries.append(dict(path=path, mode=oct(stat.S_IMODE(st.st_mode)), size=len(data), sha256=sha256(data)))
            total += len(data)
            continue
        require(stat.S_ISREG(s.st_mode), 'new path is not a regular file: ' + path)
        st, data = read_regular(worktree, path, s)
        now = '100755' if st.st_mode & stat.S_IXUSR else '100644'
        entries.append(dict(path=path, status='A', mode=now, blob=blob_id(data), sha256=sha256(data), size=len(data)))
        total += len(data)
    present = {r['path'] for r in runtime}
    require(present == set(expected), 'runtime set differs: missing %s' % sorted(set(expected) - present))
    dir_modes = {}
    wanted = dict(BASE_DIR_MODES) if lanes else {}
    for lane in lanes:
        wanted.update(LANE_DIR_MODES[lane])
    for d, want in sorted(wanted.items()):
        s = dirs.get(d)
        require(s is not None and stat.S_IMODE(s.st_mode) == want and s.st_uid == os.getuid(), 'runtime dir mode: ' + d)
        dir_modes[d] = oct(want)
    if 'codex' not in lanes:
        require(not [d for d in dirs if d == '.agents' or d.startswith('.agents/')], '.agents present before a codex segment')
    require(not any(p.startswith('.claude/.cc-writes/') for p in found), '.claude/.cc-writes is not empty')
    deleted = sorted(p for p in tree if p not in found)
    for path in deleted:
        require(PurePosixPath(path).name not in STOP_NAMES, 'stop path deleted: ' + path)
    require(len(entries) + len(deleted) + len(ignored_entries) <= MAX_FILES and total <= MAX_TOTAL_BYTES,
            'image over the bounds')
    again, again_dirs = walk(worktree)
    require(set(again) == set(found) and set(again_dirs) == set(dirs)
            and all(stat_key(again[p]) == stat_key(found[p]) for p in found), 'worktree changed during the export')
    return dict(entries=entries, deleted=deleted, ignored=ignored_entries, runtime=runtime, dir_modes=dir_modes)


def export(args):
    worktree = Path(args.worktree)
    require(str(worktree) == WORKTREE, 'unexpected worktree')
    out = outside(args.out)
    require(not out.exists(), 'output exists')
    lanes = [] if args.runtime == 'none' else args.runtime.split(',')
    require(lanes in ([], ['claude'], ['claude', 'codex']), 'runtime must be none, claude or claude,codex')
    image = dict(schema=SCHEMA, base=args.base, lanes=lanes, skill_targets=skill_targets())
    image.update(content(worktree, args.clone, args.base, lanes, args.codex_hooks_sha))
    admin = CANONICAL_GIT / 'worktrees' / worktree.name
    _, gitfile = read_regular(worktree, '.git')
    require(gitfile.decode() == 'gitdir: %s\n' % admin, 'worktree gitfile does not name the canonical admin directory')
    meta = dict(gitfile=gitfile.decode())
    for name in ('HEAD', 'gitdir', 'commondir', 'config.worktree'):
        s, data = read_file(admin / name)
        meta['admin_' + name] = dict(sha256=sha256(data), mode=oct(stat.S_IMODE(s.st_mode)), text=data.decode())
    require(meta['admin_HEAD']['text'].strip() == 'ref: refs/heads/' + BRANCH, 'worktree HEAD is not the handover branch')
    require(meta['admin_gitdir']['text'] == '%s/.git\n' % worktree, 'admin gitdir does not name the worktree')
    meta['branch_ref'] = read_file(CANONICAL_GIT / 'refs/heads' / BRANCH)[1].decode().strip()
    require(meta['branch_ref'] == args.base, 'the handover branch is not at BASE')
    meta['canonical_HEAD'] = read_file(CANONICAL_GIT / 'HEAD')[1].decode().strip()
    image['git'] = meta
    out.mkdir(mode=0o755)
    raw = (json.dumps(image, indent=1, sort_keys=True) + '\n').encode()
    (out / 'image.json').write_bytes(raw)
    print(json.dumps(dict(ok=True, image_sha256=sha256(raw), entries=len(image['entries']), deleted=len(image['deleted']),
                          ignored=len(image['ignored']), runtime=len(image['runtime']))))
    return 0


def is_control(path):
    parts = PurePosixPath(path).parts
    name = parts[-1]
    return (any(p in CONTROL_DIRS for p in parts) or name.startswith(CONTROL_NAMES_PREFIX) or name in CONTROL_NAMES
            or name.endswith('.pth') or name in STOP_NAMES)


def load(path):
    image = json.loads(Path(path).read_text())
    require(image.get('schema') == SCHEMA, 'image schema: ' + str(path))
    return image


def compare(args):
    step = STEPS[args.step]
    prev, nxt = load(args.prev), load(args.next)
    problems = []
    if prev['base'] != nxt['base']:
        problems.append('base differs')
    if prev['lanes'] != step['prev'] or nxt['lanes'] != step['next']:
        problems.append('lanes %s -> %s, expected %s -> %s' % (prev['lanes'], nxt['lanes'], step['prev'], step['next']))
    if args.step == 'C1' and (prev['entries'] or prev['deleted'] or prev['ignored'] or prev['runtime']):
        problems.append('image 0 is not the empty baseline')
    p_entries = {e['path']: e for e in prev['entries']}
    n_entries = {e['path']: e for e in nxt['entries']}
    allowed = set(step['contract']) | set(step['carry'])
    if set(n_entries) != allowed:
        problems.append('paths %s != contract %s' % (sorted(n_entries), sorted(allowed)))
    for path, status in step['contract'].items():
        if path in n_entries and n_entries[path]['status'] != status:
            problems.append('contract path %s has status %s' % (path, n_entries[path]['status']))
    for path in step['carry']:
        if p_entries.get(path) is None or p_entries.get(path) != n_entries.get(path):
            problems.append('carried contract path changed or missing: ' + path)
    if prev['deleted'] or nxt['deleted']:
        problems.append('deletions present: %s' % (prev['deleted'] + nxt['deleted']))
    for path in set(n_entries) | set(nxt['deleted']):
        if is_control(path):
            problems.append('agent-control path changed: ' + path)
    if nxt['ignored']:
        problems.append('ignored entries present: %s' % [i['path'] for i in nxt['ignored']])
    p_runtime = {r['path']: r for r in prev['runtime']}
    n_runtime = {r['path']: r for r in nxt['runtime']}
    for path, r in p_runtime.items():
        if path not in n_runtime:
            problems.append('runtime entry removed: ' + path)
        elif path not in PER_IMAGE and n_runtime[path] != r:
            problems.append('runtime entry changed: ' + path)
    if prev['lanes'] and prev['dir_modes'] != {k: v for k, v in nxt['dir_modes'].items() if k in prev['dir_modes']}:
        problems.append('runtime directory modes changed')
    if prev['skill_targets'] != nxt['skill_targets']:
        problems.append('skill target content changed')
    for key in ('gitfile', 'admin_gitdir', 'admin_commondir', 'admin_HEAD', 'admin_config.worktree', 'branch_ref',
                'canonical_HEAD'):
        if prev['git'].get(key) != nxt['git'].get(key):
            problems.append('git metadata changed: ' + key)
    print(json.dumps(dict(ok=not problems, problems=problems)))
    return 0 if not problems else 1


def verify(args):
    image = load(args.image)
    copy = outside(args.copy)
    hooks = next((r['sha256'] for r in image['runtime'] if r['path'] == '.codex/hooks.json'), None)
    got = content(copy, args.clone, image['base'], image['lanes'], hooks)
    problems = [k for k in ('entries', 'deleted', 'ignored', 'runtime', 'dir_modes') if got[k] != image[k]]
    print(json.dumps(dict(ok=not problems, differs=problems)))
    return 0 if not problems else 1


def holder(args):
    image = load(args.image)
    raw = Path(args.image).read_bytes()
    entries = {e['path']: e for e in image['entries']}
    paths = STEPS[args.step]['contract'] if args.step == 'C1' else \
        dict(list(STEPS['X']['contract'].items()) + [(p, None) for p in STEPS['X']['carry']])
    lines = ['gct-oak5 handover image after %s, schema %s, image sha256 %s' % (args.step, SCHEMA, sha256(raw)), '']
    for path in sorted(paths):
        require(path in entries, 'path not in the image: ' + path)
        lines.append('DIGEST %s %s' % (path, entries[path]['sha256']))
    print('\n'.join(lines))
    return 0


def main(argv):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export')
    for flag in ('--worktree', '--clone', '--base', '--out', '--runtime'):
        e.add_argument(flag, required=True)
    e.add_argument('--codex-hooks-sha')
    c = sub.add_parser('compare')
    c.add_argument('--step', required=True, choices=sorted(STEPS))
    c.add_argument('--prev', required=True)
    c.add_argument('--next', required=True)
    v = sub.add_parser('verify')
    for flag in ('--image', '--copy', '--clone'):
        v.add_argument(flag, required=True)
    h = sub.add_parser('holder')
    h.add_argument('--image', required=True)
    h.add_argument('--step', required=True, choices=('C1', 'X'))
    args = parser.parse_args(argv)
    try:
        return dict(export=export, compare=compare, verify=verify, holder=holder)[args.cmd](args)
    except Exception as exc:  # every failure is a refusal with a reason, never a traceback
        print(json.dumps(dict(ok=False, refused='%s: %s' % (type(exc).__name__, exc))))
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
