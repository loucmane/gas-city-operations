"""gct-oak5 handover image tool (plan r16, "Handover images and the route gate").

  image_tool.py export  --worktree W --clone C --base B --out O --runtime none|claude|claude,codex [--codex-hooks-sha S]
  image_tool.py compare --prev P.json --next N.json --contract PATH:STATUS,... [--carry PATH,...]
  image_tool.py holder  --manifest M.json --paths PATH,...

export reads the handover worktree with no git anywhere under it (the gct-mbg6 intake method): it walks
directory descriptors without following links and compares every entry with the BASE tree read from a bare
GitHub clone. Ignored status comes from BASE's .gitignore files in a scratch mirror. It writes <out>/image.json:
- entries: every modified (M) or added (A) path, with mode, blob id, sha256 and size;
- deleted: tracked paths that are missing;
- ignored: every ignored entry that is not RUNTIME, with type, mode, size and sha256 (links, hard links and
  special files among them refuse);
- runtime: every RUNTIME entry, checked against the pins below for the lanes named by --runtime;
- git: the worktree .git gitfile bytes, the admin HEAD, gitdir, commondir and config.worktree bytes, the
  branch ref and the canonical HEAD, all read as files.
It refuses a nested `.git` path component (any case), a stop path change, and output under a forbidden root.

compare implements route-gate rules 2 to 4 between two images: the delta is exactly the contract (every other
path unchanged; --carry names contract paths of an earlier segment that must be unchanged), no agent-control
path changes beyond admitted RUNTIME, and no ignored entry other than RUNTIME. It exits non-zero on refusal.

holder prints the DIGEST lines for the given paths from an image, for the image holder's description.

Limits (plan): empty directories and group or other mode bits are not recorded.
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

SCHEMA = 'gct-oak5.handover-image.v1'
WORKTREE = '/home/loucmane/gas-city-template-candidate-worktrees/gct-oak5'
CANONICAL_GIT = Path('/home/loucmane/gas-city-template/.git')
FORBIDDEN_ROOTS = (Path('/home/loucmane/vaults/main/GasCity'), Path('/home/loucmane/gas-city-template-worktrees'),
                   Path('/home/loucmane/gas-city-template-candidate-worktrees'), Path('/home/loucmane/gas-city-template'),
                   Path('/home/loucmane/.local/share/gas-city-staging/gct-oak5-handover/probe-target'),
                   Path('/tmp'), Path('/var/tmp'), Path('/dev/shm'))
STOP_NAMES = ('.gitignore', '.gitattributes', '.gitmodules', '.lfsconfig')
CONTROL_TOPS = ('.codex/', '.agents/', '.claude/', '.gc/')
CONTROL_NAMES_PREFIX = ('AGENTS', 'CLAUDE')
CONTROL_NAMES = ('.mcp.json', 'conftest.py', 'sitecustomize.py')
MAX_FILES = 1000
MAX_FILE_BYTES = 8 << 20
MAX_TOTAL_BYTES = 32 << 20
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
CACHE = '/home/loucmane/gascity/home/cache/repos/'
SKILL_MAP = {f'core.gc-{n}': CACHE + '69fe9a2e6239743677a6e13188096df34d6eb6d41fad171af58671ef288fdd3f/internal/bootstrap/packs/core/skills/gc-' + n
             for n in ('agents', 'city', 'dashboard', 'dispatch', 'mail', 'rigs', 'work')}
SKILL_MAP['gascity.mayor'] = CACHE + '954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/gascity/skills/mayor'
OWNED_ROOTS = [CACHE + '69fe9a2e6239743677a6e13188096df34d6eb6d41fad171af58671ef288fdd3f/internal/bootstrap/packs/core/skills',
               CACHE + '954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/gascity/skills']
OWNERSHIP_BYTES = json.dumps({'targets': SKILL_MAP}, separators=(',', ':'), sort_keys=True).encode()
CITY_FILES = {'.gc/settings.json': ('/home/loucmane/gascity/city/.gc/settings.json', 0o644),
              '.gc/scripts/mol-dog-stale-db.sh': ('/home/loucmane/gascity/city/.gc/scripts/mol-dog-stale-db.sh', 0o755)}
LANES = {
    'claude': {'sink': '.claude/skills', 'catalog': '.gc/tmp/skill-catalog-gas-city-template_gc.implementation-worker.b64'},
    'codex': {'sink': '.agents/skills', 'catalog': '.gc/tmp/skill-catalog-gas-city-template_codex.b64'},
}
DIR_MODES = {'.gc': 0o700, '.gc/tmp': 0o700, '.gc/scripts': 0o755, '.agents': 0o755, '.agents/skills': 0o755,
             '.codex': 0o755}


class Refusal(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise Refusal(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def blob_id(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


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
    """Every non-directory entry under root, by descriptor, never following a link: ({path: lstat}, {dir: lstat})."""
    entries, dirs = {}, {}

    def visit(fd, rel):
        for name in sorted(os.listdir(fd)):
            path = rel + '/' + name if rel else name
            s = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if not rel and name == '.git':
                require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'worktree .git is not a single-link gitfile')
                continue
            require(name.lower() != '.git', 'nested .git component: ' + path)
            if stat.S_ISDIR(s.st_mode):
                dirs[path] = s
                sub = os.open(name, DIR_FLAGS, dir_fd=fd)
                try:
                    visit(sub, path)
                finally:
                    os.close(sub)
            else:
                entries[path] = s
    fd = os.open(root, DIR_FLAGS)
    try:
        visit(fd, '')
        return entries, dirs
    finally:
        os.close(fd)


def open_parent(root, path):
    parts = PurePosixPath(path).parts
    fd = os.open(root, DIR_FLAGS)
    for part in parts[:-1]:
        nxt = os.open(part, DIR_FLAGS, dir_fd=fd)
        os.close(fd)
        fd = nxt
    return fd, parts[-1]


def read_regular(root, path):
    """(lstat, bytes) of a single-link regular file, opened component by component with O_NOFOLLOW."""
    fd, name = open_parent(root, path)
    try:
        f = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=fd)
        try:
            s = os.fstat(f)
            require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'not a single-link regular file: ' + path)
            require(s.st_size <= MAX_FILE_BYTES, 'file over the bound: ' + path)
            chunks = []
            while True:
                chunk = os.read(f, 1 << 20)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b''.join(chunks)
            require(len(data) == s.st_size and os.fstat(f).st_size == s.st_size, 'file changed while read: ' + path)
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
    """Bytes of a single-link regular file outside the worktree (git metadata, city files), no following."""
    f = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOATIME)
    try:
        s = os.fstat(f)
        require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'not a single-link regular file: ' + str(path))
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
        expected[sink + '/.gc-skill-ownership.json'] = dict(kind='file', mode=0o644, sha256=sha256(OWNERSHIP_BYTES))
        for name, target in SKILL_MAP.items():
            expected[sink + '/' + name] = dict(kind='link', target=target)
        expected[LANES[lane]['catalog']] = dict(kind='catalog', mode=0o600)
    if 'codex' in lanes:
        require(codex_hooks_sha, '--codex-hooks-sha is required for the codex lane')
        expected['.codex/hooks.json'] = dict(kind='file', mode=0o644, sha256=codex_hooks_sha)
    return expected


def check_targets():
    for name, target in SKILL_MAP.items():
        require(os.path.realpath(target) == target and '/../' not in target and '/./' not in target,
                'skill target is not a clean real path: ' + target)
        s = os.lstat(target)
        require(stat.S_ISDIR(s.st_mode) and s.st_uid == os.getuid(), 'skill target is not an operator directory: ' + target)
        require(stat.S_ISREG(os.lstat(target + '/SKILL.md').st_mode), 'skill target has no SKILL.md: ' + target)


def catalog_ok(data):
    try:
        value = json.loads(base64.b64decode(data, validate=True))
    except (ValueError, TypeError):
        return False
    if set(value) != {'Entries', 'OwnedRoots', 'Shadowed'} or value['Shadowed'] is not None:
        return False
    if value['OwnedRoots'] != OWNED_ROOTS:
        return False
    entries = value['Entries']
    return (isinstance(entries, list) and sorted(e.get('Name') for e in entries) == sorted(SKILL_MAP)
            and all(set(e) == {'Name', 'Source', 'Origin', 'Description'} and e['Source'] == SKILL_MAP[e['Name']]
                    for e in entries))


def is_runtime_namespace(path, tree):
    return path.startswith(('.gc/', '.agents/', '.codex/', '.claude/')) and path not in tree


def export(args):
    worktree = Path(args.worktree)
    require(str(worktree) == WORKTREE, 'unexpected worktree')
    out = outside(args.out)
    require(not out.exists(), 'output exists')
    clone = check_clone(args.clone, args.base)
    lanes = [] if args.runtime == 'none' else args.runtime.split(',')
    require(lanes in ([], ['claude'], ['claude', 'codex']), 'runtime must be none, claude or claude,codex')
    check_targets()
    tree = base_tree(clone, args.base)
    found, dirs = walk(worktree)
    scratch = outside(out.parent / (out.name + '.scratch'))
    require(not scratch.exists(), 'scratch exists')
    scratch.mkdir(mode=0o700)
    try:
        candidates = [p for p in sorted(found) if p not in tree]
        ignore = ignored(clone, tree, dirs, candidates, scratch)
    finally:
        scratch.rmdir()

    expected = expected_runtime(lanes, args.codex_hooks_sha)
    runtime, entries, ignored_entries, total = [], [], [], 0
    for path in sorted(found):
        s = found[path]
        if path in tree:
            mode, oid = tree[path]
            if mode == '120000':
                require(stat.S_ISLNK(s.st_mode) and blob_id(readlink_at(worktree, path).encode()) == oid,
                        'tracked link changed: ' + path)
                continue
            require(stat.S_ISREG(s.st_mode), 'tracked file is not a regular file: ' + path)
            st, data = read_regular(worktree, path)
            now = '100755' if st.st_mode & stat.S_IXUSR else '100644'
            if blob_id(data) == oid and now == mode:
                continue
            require(PurePosixPath(path).name not in STOP_NAMES, 'stop path changed: ' + path)
            entries.append(dict(path=path, status='M', mode=now, blob=blob_id(data), sha256=sha256(data), size=len(data)))
            total += len(data)
            continue
        if path in expected:
            spec = expected[path]
            if spec['kind'] == 'link':
                require(stat.S_ISLNK(s.st_mode) and readlink_at(worktree, path) == spec['target'],
                        'runtime link differs: ' + path)
                runtime.append(dict(path=path, kind='link', target=spec['target']))
            else:
                st, data = read_regular(worktree, path)
                require(stat.S_IMODE(st.st_mode) == spec['mode'] and st.st_uid == os.getuid(), 'runtime mode: ' + path)
                if spec['kind'] == 'catalog':
                    require(catalog_ok(data), 'runtime catalog differs: ' + path)
                else:
                    require(sha256(data) == spec['sha256'], 'runtime bytes differ: ' + path)
                runtime.append(dict(path=path, kind=spec['kind'], mode=oct(spec['mode']), sha256=sha256(data)))
            continue
        require(not is_runtime_namespace(path, tree), 'unadmitted control-namespace entry: ' + path)
        if path in ignore:
            require(stat.S_ISREG(s.st_mode), 'ignored entry is not a regular file: ' + path)
            st, data = read_regular(worktree, path)
            ignored_entries.append(dict(path=path, mode=oct(stat.S_IMODE(st.st_mode)), size=len(data), sha256=sha256(data)))
            continue
        require(PurePosixPath(path).name not in STOP_NAMES, 'stop path added: ' + path)
        require(stat.S_ISREG(s.st_mode), 'new path is not a regular file: ' + path)
        st, data = read_regular(worktree, path)
        now = '100755' if st.st_mode & stat.S_IXUSR else '100644'
        entries.append(dict(path=path, status='A', mode=now, blob=blob_id(data), sha256=sha256(data), size=len(data)))
        total += len(data)
    present = {r['path'] for r in runtime}
    require(present == set(expected), 'runtime set differs: missing %s' % sorted(set(expected) - present))
    for d, want in DIR_MODES.items() if lanes else ():
        if d.startswith('.agents') or d == '.codex':
            if 'codex' not in lanes:
                continue
        s = dirs.get(d)
        require(s is not None and stat.S_IMODE(s.st_mode) == want and s.st_uid == os.getuid(), 'runtime dir mode: ' + d)
    if 'codex' not in lanes:
        require(not [d for d in dirs if d == '.agents' or d.startswith('.agents/')],
                '.agents present before a codex segment')
    cc = dirs.get('.claude/.cc-writes')
    require(cc is None or not any(p.startswith('.claude/.cc-writes/') for p in found), '.claude/.cc-writes is not empty')
    deleted = sorted(p for p in tree if p not in found)
    for path in deleted:
        require(PurePosixPath(path).name not in STOP_NAMES, 'stop path deleted: ' + path)
    require(len(entries) + len(deleted) <= MAX_FILES and total <= MAX_TOTAL_BYTES, 'image over the bounds')

    admin = CANONICAL_GIT / 'worktrees' / worktree.name
    _, gitfile = read_regular(worktree, '.git')
    git_meta = dict(gitfile=gitfile.decode())
    for name in ('HEAD', 'gitdir', 'commondir', 'config.worktree'):
        s, data = read_file(admin / name)
        git_meta['admin_' + name] = dict(sha256=sha256(data), mode=oct(stat.S_IMODE(s.st_mode)), text=data.decode(errors='replace'))
    head = git_meta['admin_HEAD']['text'].strip()
    require(head == 'ref: refs/heads/codex/gct-oak5-handover-proof', 'worktree HEAD is not the handover branch')
    branch = CANONICAL_GIT / 'refs/heads/codex/gct-oak5-handover-proof'
    git_meta['branch_ref'] = read_file(branch)[1].decode().strip()
    git_meta['canonical_HEAD'] = read_file(CANONICAL_GIT / 'HEAD')[1].decode().strip()

    out.mkdir(mode=0o755)
    image = dict(schema=SCHEMA, base=args.base, worktree=str(worktree), lanes=lanes, entries=entries,
                 deleted=deleted, ignored=ignored_entries, runtime=runtime, git=git_meta)
    raw = (json.dumps(image, indent=1, sort_keys=True) + '\n').encode()
    (out / 'image.json').write_bytes(raw)
    print(json.dumps(dict(ok=True, image_sha256=sha256(raw), entries=len(entries), deleted=len(deleted),
                          ignored=len(ignored_entries), runtime=len(runtime))))


def is_control(path):
    name = PurePosixPath(path).name
    return (path.startswith(CONTROL_TOPS) or name.startswith(CONTROL_NAMES_PREFIX) or name in CONTROL_NAMES
            or name.endswith('.pth') or name in STOP_NAMES)


def load(path):
    image = json.loads(Path(path).read_text())
    require(image.get('schema') == SCHEMA, 'image schema: ' + str(path))
    return image


def compare(args):
    prev, nxt = load(args.prev), load(args.next)
    require(prev['base'] == nxt['base'] and prev['worktree'] == nxt['worktree'], 'base or worktree differs')
    contract = {}
    for item in args.contract.split(','):
        path, status = item.rsplit(':', 1)
        contract[path] = status
    carry = set(filter(None, (args.carry or '').split(',')))
    p_entries = {e['path']: e for e in prev['entries']}
    n_entries = {e['path']: e for e in nxt['entries']}
    problems = []
    for path in set(p_entries) | set(n_entries):
        if path in contract:
            continue
        if p_entries.get(path) != n_entries.get(path):
            problems.append('path outside the contract changed: ' + path)
    for path, status in contract.items():
        e = n_entries.get(path)
        if e is None or e['status'] != status:
            problems.append('contract path not changed as declared: %s %s' % (path, status))
    for path in carry:
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
    for r in nxt['runtime']:
        if r['path'] in p_runtime and p_runtime[r['path']] != r:
            problems.append('runtime entry changed: ' + r['path'])
    missing = set(p_runtime) - {r['path'] for r in nxt['runtime']}
    if missing:
        problems.append('runtime entries removed: %s' % sorted(missing))
    for key in ('gitfile', 'admin_gitdir', 'admin_commondir', 'admin_HEAD', 'admin_config.worktree', 'branch_ref',
                'canonical_HEAD'):
        if prev['git'].get(key) != nxt['git'].get(key):
            problems.append('git metadata changed: ' + key)
    print(json.dumps(dict(ok=not problems, problems=problems)))
    return 0 if not problems else 1


def holder(args):
    image = load(args.manifest)
    entries = {e['path']: e for e in image['entries']}
    raw = Path(args.manifest).read_bytes()
    lines = ['gct-oak5 handover image, schema %s, image sha256 %s' % (SCHEMA, sha256(raw)), '']
    for path in args.paths.split(','):
        require(path in entries, 'path not in the image: ' + path)
        lines.append('DIGEST %s %s' % (path, entries[path]['sha256']))
    print('\n'.join(lines))


def main(argv):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export')
    e.add_argument('--worktree', required=True)
    e.add_argument('--clone', required=True)
    e.add_argument('--base', required=True)
    e.add_argument('--out', required=True)
    e.add_argument('--runtime', required=True)
    e.add_argument('--codex-hooks-sha')
    c = sub.add_parser('compare')
    c.add_argument('--prev', required=True)
    c.add_argument('--next', required=True)
    c.add_argument('--contract', required=True)
    c.add_argument('--carry')
    h = sub.add_parser('holder')
    h.add_argument('--manifest', required=True)
    h.add_argument('--paths', required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == 'export':
            export(args)
            return 0
        if args.cmd == 'compare':
            return compare(args)
        holder(args)
        return 0
    except Refusal as exc:
        print(json.dumps(dict(ok=False, refused=str(exc))))
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
