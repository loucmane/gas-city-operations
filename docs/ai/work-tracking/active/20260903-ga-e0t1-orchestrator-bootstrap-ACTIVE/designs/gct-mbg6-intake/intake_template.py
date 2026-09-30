"""No-git intake of one Template codex worktree (gct-e8ex-window README, run order step 6).

  intake_template.py export <worktree> <base-clone> <base> <out-dir>
  intake_template.py tree   <base-clone> <base> <export-dir> <manifest-sha256>
  intake_template.py stage  <sign-clone> <base> <export-dir> <tree-json-sha256>

- export reads the worker's worktree without running git anywhere under it. It walks directory descriptors
  without following links and compares every regular file with the BASE tree, read from a bare clone fetched from
  GitHub (no alternates, replace objects off). Ignored status comes from BASE's own .gitignore files, evaluated
  by `git check-ignore --no-index` in a scratch mirror that holds only those files and the directory skeleton.
  It refuses links, hard links, FIFOs, devices and sockets on any exported path, any change to a stop path
  (.gitignore, .gitattributes, .gitmodules, .lfsconfig) and any excess over the bounds. It writes the export
  directory: files/<path> with the exact bytes, and manifest.json. It prints the manifest digest.
- tree verifies the manifest digest and every exported byte, then computes the reviewed tree id in a scratch
  index of the bare clone and writes review.diff (git diff BASE <tree>, no textconv, no external diff) and
  tree.json. It prints the tree.json digest.
- stage writes the reviewed bytes into a standalone non-bare clone at BASE, stages exactly the manifest paths
  with hardened git, and requires `git write-tree` to equal the reviewed tree. The signed commit, push and pull
  request follow by hand.

Every git run uses an empty environment, no system or global config, hooks and fsmonitor off, no optional locks
and GIT_NO_REPLACE_OBJECTS=1. No output may sit under a codex write root or a shared temporary directory.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys

SCHEMA = 'gct-mbg6.template-intake.v1'
FORBIDDEN_ROOTS = (Path('/home/loucmane/vaults/main/GasCity'), Path('/home/loucmane/gas-city-template-worktrees'),
                   Path('/home/loucmane/gas-city-template'), Path('/tmp'), Path('/var/tmp'), Path('/dev/shm'))
# Session runtime, written by gc for every managed session (codex hooks and the skills sink). Recorded, never
# exported. Anything else that is neither ignored nor unchanged is exported or refused.
RUNTIME = ('.codex/hooks.json', '.agents/skills/')
STOP_NAMES = ('.gitignore', '.gitattributes', '.gitmodules', '.lfsconfig')
MAX_FILES = 1000
MAX_FILE_BYTES = 8 << 20
MAX_TOTAL_BYTES = 32 << 20
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


class Refusal(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise Refusal(message)


def git(repo, *args, stdin=None, env=None, bare=True):
    base = ['/usr/bin/git', '--no-optional-locks', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
            '-c', 'core.attributesFile=/dev/null', '-c', 'core.excludesFile=/dev/null']
    base += ['--git-dir', str(repo)] if bare else ['-C', str(repo)]
    environment = dict(HOME='/nonexistent', PATH='/usr/bin:/bin', LANG='C.UTF-8', GIT_CONFIG_NOSYSTEM='1',
                       GIT_CONFIG_GLOBAL='/dev/null', GIT_ATTR_NOSYSTEM='1', GIT_NO_REPLACE_OBJECTS='1',
                       GIT_TERMINAL_PROMPT='0', **(env or {}))
    r = subprocess.run(base + list(args), input=stdin, capture_output=True, env=environment, timeout=300)
    require(r.returncode == 0, 'git %s: %s' % (args[0], r.stderr.decode(errors='replace')[-400:]))
    return r.stdout


def outside(path):
    real = Path(os.path.realpath(path))
    for root in FORBIDDEN_ROOTS:
        require(real != root and root not in real.parents, 'output under a forbidden root: ' + str(path))
    return real


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def blob_id(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def check_clone(clone, base):
    require(not (Path(clone) / 'objects/info/alternates').exists(), 'clone has alternates')
    require(not list((Path(clone) / 'refs/replace').glob('**/*')) if (Path(clone) / 'refs/replace').exists()
            else True, 'clone has replace refs')
    require(git(clone, 'rev-parse', '--verify', base + '^{commit}').decode().strip() == base, 'BASE missing')


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
    """Every non-directory entry under root, by descriptor, never following a link: ({path: lstat}, {dirs})."""
    entries = {}
    dirs = set()

    def visit(fd, rel):
        for name in sorted(os.listdir(fd)):
            path = rel + '/' + name if rel else name
            if not rel and name == '.git':
                s = os.stat(name, dir_fd=fd, follow_symlinks=False)
                require(stat.S_ISREG(s.st_mode), 'worktree .git is not a gitfile')
                continue
            s = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(s.st_mode):
                dirs.add(path)
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


def read_regular(root, path):
    """Open path under root one component at a time with O_NOFOLLOW; return (lstat, bytes)."""
    parts = PurePosixPath(path).parts
    fd = os.open(root, DIR_FLAGS)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = nxt
        f = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=fd)
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
    parts = PurePosixPath(path).parts
    fd = os.open(root, DIR_FLAGS)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return os.readlink(parts[-1], dir_fd=fd)
    finally:
        os.close(fd)


def ignored(clone, base, tree, dirs, paths, scratch, nested=None):
    """BASE's .gitignore rules (plus admitted nested ones) applied to paths, in a mirror holding only those files
    and the directory skeleton."""
    if not paths:
        return set()
    mirror = scratch / 'mirror'
    mirror.mkdir(mode=0o700)
    for d in sorted(dirs):
        (mirror / d).mkdir(mode=0o700, exist_ok=True)
    for path, (mode, oid) in tree.items():
        if PurePosixPath(path).name == '.gitignore':
            target = mirror / path
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(git(clone, 'cat-file', 'blob', oid))
    for path, data in (nested or {}).items():
        (mirror / path).write_bytes(data)
    r = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-c', 'core.hooksPath=/dev/null', '-c',
                        'core.fsmonitor=false', '-c', 'core.excludesFile=/dev/null', '--git-dir', str(clone),
                        '--work-tree', str(mirror), 'check-ignore', '--no-index', '-z', '--stdin'],
                       input=b'\0'.join(p.encode() for p in paths) + b'\0', capture_output=True, timeout=300,
                       env=dict(HOME='/nonexistent', PATH='/usr/bin:/bin', GIT_CONFIG_NOSYSTEM='1',
                                GIT_CONFIG_GLOBAL='/dev/null', GIT_NO_REPLACE_OBJECTS='1'))
    require(r.returncode in (0, 1), 'check-ignore: ' + r.stderr.decode(errors='replace')[-300:])
    shutil.rmtree(mirror)
    return {p.decode() for p in r.stdout.split(b'\0') if p}


def runtime(path):
    return path in RUNTIME or any(path.startswith(p) for p in RUNTIME if p.endswith('/'))


def export(worktree, clone, base, out):
    worktree = Path(worktree)
    out = outside(out)
    require(not out.exists(), 'export directory exists')
    check_clone(clone, base)
    tree = base_tree(clone, base)
    found, dirs = walk(worktree)
    scratch = out.parent / (out.name + '.scratch')
    require(not scratch.exists(), 'scratch exists')
    scratch.mkdir(mode=0o700)
    candidates = [p for p in sorted(found) if p not in tree and not runtime(p)]
    # An untracked nested .gitignore (pytest's .pytest_cache marker is the known case) is applied as git would,
    # but only when it ignores itself, so it can hide nothing but its own tool-private directory; any other new
    # .gitignore is a stop path below.
    nested = {p: read_regular(worktree, p)[1] for p in candidates
              if PurePosixPath(p).name == '.gitignore' and '/' in p}
    ignore = ignored(clone, base, tree, dirs, candidates, scratch, nested)
    scratch.rmdir()
    for path in nested:
        require(path in ignore, 'nested .gitignore does not ignore itself: ' + path)
    entries, excluded, total = [], [], 0
    for path in sorted(found):
        s = found[path]
        if runtime(path):
            kind = 'link' if stat.S_ISLNK(s.st_mode) else 'file'
            detail = readlink_at(worktree, path) if kind == 'link' else sha256(read_regular(worktree, path)[1])
            excluded.append(dict(path=path, kind=kind, detail=detail))
            continue
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
            entries.append(dict(path=path, status='M', mode=now, blob=blob_id(data), sha256=sha256(data),
                                size=len(data)))
        elif path in ignore:
            continue
        else:
            require(PurePosixPath(path).name not in STOP_NAMES, 'stop path added: ' + path)
            require(stat.S_ISREG(s.st_mode), 'new path is not a regular file: ' + path)
            st, data = read_regular(worktree, path)
            now = '100755' if st.st_mode & stat.S_IXUSR else '100644'
            entries.append(dict(path=path, status='A', mode=now, blob=blob_id(data), sha256=sha256(data),
                                size=len(data)))
        total += entries[-1]['size']
    deleted = sorted(p for p in tree if p not in found)
    for path in deleted:
        require(PurePosixPath(path).name not in STOP_NAMES, 'stop path deleted: ' + path)
    require(len(entries) + len(deleted) <= MAX_FILES and total <= MAX_TOTAL_BYTES, 'export over the bounds')
    out.mkdir(mode=0o755)
    for e in entries:
        target = out / 'files' / e['path']
        target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        data = read_regular(worktree, e['path'])[1]
        require(sha256(data) == e['sha256'], 'file changed during export: ' + e['path'])
        target.write_bytes(data)
    manifest = dict(schema=SCHEMA, base=base, worktree=str(worktree), entries=entries, deleted=deleted,
                    excluded=excluded, nested_ignore={p: sha256(b) for p, b in sorted(nested.items())},
                    ignored_count=len(ignore),
                    ignored_sha256=sha256('\0'.join(sorted(ignore)).encode()))
    raw = (json.dumps(manifest, indent=1, sort_keys=True) + '\n').encode()
    (out / 'manifest.json').write_bytes(raw)
    print(json.dumps(dict(ok=True, manifest_sha256=sha256(raw), exported=len(entries), deleted=len(deleted),
                          excluded=len(excluded), ignored=len(ignore))))


def load_export(export_dir, manifest_sha):
    export_dir = Path(export_dir)
    raw = (export_dir / 'manifest.json').read_bytes()
    require(sha256(raw) == manifest_sha, 'manifest digest')
    manifest = json.loads(raw)
    require(manifest['schema'] == SCHEMA, 'manifest schema')
    listed = {e['path'] for e in manifest['entries']}
    present = {str(p.relative_to(export_dir / 'files')) for p in (export_dir / 'files').rglob('*') if p.is_file()}
    require(listed == present, 'export files differ from the manifest')
    data = {}
    for e in manifest['entries']:
        p = export_dir / 'files' / e['path']
        require(not p.is_symlink(), 'exported link')
        b = p.read_bytes()
        require(sha256(b) == e['sha256'] and blob_id(b) == e['blob'] and len(b) == e['size'], 'export bytes: ' + e['path'])
        require(e['mode'] in ('100644', '100755') and e['status'] in ('A', 'M'), 'entry shape')
        data[e['path']] = b
    return manifest, data


def tree_cmd(clone, base, export_dir, manifest_sha):
    check_clone(clone, base)
    manifest, data = load_export(export_dir, manifest_sha)
    require(manifest['base'] == base, 'manifest base')
    index = outside(Path(export_dir).parent / (Path(export_dir).name + '.index'))
    require(not index.exists(), 'scratch index exists')
    # update-index needs a work tree even for --cacheinfo; an empty directory keeps every byte from the export.
    empty = outside(Path(export_dir).parent / (Path(export_dir).name + '.empty'))
    empty.mkdir(mode=0o700)
    env = dict(GIT_INDEX_FILE=str(index), GIT_WORK_TREE=str(empty))
    try:
        git(clone, 'read-tree', base, env=env)
        for e in manifest['entries']:
            oid = git(clone, 'hash-object', '-w', '--no-filters', '--stdin', stdin=data[e['path']]).decode().strip()
            require(oid == e['blob'], 'blob id ' + e['path'])
            git(clone, 'update-index', '--add', '--cacheinfo', '%s,%s,%s' % (e['mode'], oid, e['path']), env=env)
        for path in manifest['deleted']:
            git(clone, 'update-index', '--force-remove', '--', path, env=env)
        tree = git(clone, 'write-tree', env=env).decode().strip()
    finally:
        if index.exists():
            index.unlink()
        empty.rmdir()
    diff = git(clone, 'diff', '--no-ext-diff', '--no-textconv', '--binary', '--full-index', base, tree)
    (Path(export_dir) / 'review.diff').write_bytes(diff)
    result = dict(schema=SCHEMA, base=base, tree=tree, manifest_sha256=manifest_sha, diff_sha256=sha256(diff))
    raw = (json.dumps(result, indent=1, sort_keys=True) + '\n').encode()
    (Path(export_dir) / 'tree.json').write_bytes(raw)
    print(json.dumps(dict(ok=True, tree=tree, tree_json_sha256=sha256(raw))))


def stage(clone, base, export_dir, tree_sha):
    clone = outside(clone)
    raw = (Path(export_dir) / 'tree.json').read_bytes()
    require(sha256(raw) == tree_sha, 'tree.json digest')
    reviewed = json.loads(raw)
    require(reviewed['base'] == base, 'tree base')
    manifest, data = load_export(export_dir, reviewed['manifest_sha256'])
    require(not (clone / '.git/objects/info/alternates').exists(), 'sign clone has alternates')
    require(git(clone, 'rev-parse', 'HEAD', bare=False).decode().strip() == base, 'sign clone HEAD is not BASE')
    require(git(clone, 'status', '--porcelain', '--untracked-files=all', bare=False) == b'', 'sign clone not clean')
    for e in manifest['entries']:
        target = clone / e['path']
        require(not target.is_symlink(), 'sign clone link at ' + e['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data[e['path']])
        os.chmod(target, 0o755 if e['mode'] == '100755' else 0o644)
    for path in manifest['deleted']:
        (clone / path).unlink()
    paths = [e['path'] for e in manifest['entries']] + manifest['deleted']
    git(clone, 'add', '-A', '--', *paths, bare=False)
    tree = git(clone, 'write-tree', bare=False).decode().strip()
    require(tree == reviewed['tree'], 'staged tree %s differs from the reviewed %s' % (tree, reviewed['tree']))
    require(git(clone, 'status', '--porcelain', '--untracked-files=all', bare=False).decode().count('\n')
            == len(paths), 'unexpected worktree changes in the sign clone')
    print(json.dumps(dict(ok=True, tree=tree, staged=len(paths))))


def main(argv):
    if len(argv) == 5 and argv[0] == 'export':
        export(*argv[1:])
    elif len(argv) == 5 and argv[0] == 'tree':
        tree_cmd(*argv[1:])
    elif len(argv) == 5 and argv[0] == 'stage':
        stage(Path(argv[1]), *argv[2:])
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
