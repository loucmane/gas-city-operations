"""gct-oak5 handover image tool r3 (plan r18, "Handover images and the route gate").

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
- skill_targets: length-prefixed digests of every pinned skill tree, including file/directory modes and .git names;
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
image's lanes and settings digest and requires every content field to equal the image (the copy's own path
is normalised).

holder prints the DIGEST lines of the step's contract paths from an image, for the image holder.

The common .git/config, hooks, info/* and admin index belong to the separate common snapshot, not this image.
Schema v3 deliberately refuses historical v2 images; their skill digests must not be reinterpreted.

Bounds: directory enumeration stops at MAX_WALK entries (including the root gitfile), at MAX_DEPTH levels;
regular reads stop at their observed size (at most MAX_FILE_BYTES) plus one sentinel byte. MAX_TOTAL_BYTES
bounds accepted regular content per worktree or skill tree, including unchanged and RUNTIME files; a failed
read may consume one extra sentinel byte. MAX_FILES
bounds modified, added, deleted and ignored image rows. These are input bounds, not a process memory limit.
Limits: empty directories outside RUNTIME and full permission bits of contract entries are not recorded.
Contract entries record only git's 100644/100755; skill trees record all permission bits and empty directories.
An operator-owned, non-group/other-writable empty .claude/.cc-writes directory is admitted for the Claude lane;
its presence is not part of RUNTIME. Every descendant, link, special file or unsafe mode there refuses.
"""
import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys

SCHEMA = 'gct-oak5.handover-image.v3'
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


def walk(root, *, skill=False):
    """Bounded descriptor walk; only skill targets may contain ordinary .git names."""
    entries, dirs = {}, {}
    count = 0

    def visit(fd, rel, depth):
        nonlocal count
        require(depth <= MAX_DEPTH, 'directory depth over the bound at ' + rel)
        with os.scandir(fd) as scan:
            for entry in scan:
                count += 1
                require(count <= MAX_WALK, 'walk over the bound')
                name = entry.name
                path = rel + '/' + name if rel else name
                path.encode('utf-8')
                s = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if not skill:
                    if not rel and name == '.git':
                        require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1,
                                'worktree .git is not a single-link gitfile')
                        continue
                    require(name.lower() != '.git', 'nested .git component: ' + path)
                if stat.S_ISDIR(s.st_mode):
                    dirs[path] = s
                    sub = os.open(name, DIR_FLAGS, dir_fd=fd)
                    try:
                        require(stat_key(os.fstat(sub)) == stat_key(s), 'directory changed after walk: ' + path)
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


def read_bounded(fd, path, lstat_before=None, remaining=None):
    """Read at most the observed size plus one byte, with pre-read budget and post-read stat checks."""
    s = os.fstat(fd)
    require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'not a single-link regular file: ' + str(path))
    limit = MAX_FILE_BYTES if remaining is None else min(MAX_FILE_BYTES, remaining)
    require(s.st_size <= limit, 'file or total bytes over the bound: ' + str(path))
    if lstat_before is not None:
        require(stat_key(s) == stat_key(lstat_before), 'file changed after the walk: ' + str(path))
    chunks, size = [], 0
    while True:
        chunk = os.read(fd, min(1 << 20, s.st_size - size + 1))
        if not chunk:
            break
        size += len(chunk)
        require(size <= s.st_size, 'file changed while read (size bound): ' + str(path))
        chunks.append(chunk)
    require(size == s.st_size and stat_key(os.fstat(fd)) == stat_key(s), 'file changed while read: ' + str(path))
    return s, b''.join(chunks)


def read_regular(root, path, lstat_before=None, remaining=None):
    """Single-link regular file, opened component by component with O_NOFOLLOW."""
    fd, name = open_parent(root, path)
    try:
        f = os.open(name, FILE_FLAGS, dir_fd=fd)
        try:
            return read_bounded(f, path, lstat_before, remaining)
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
    """Bounded single-link regular file outside the worktree (git metadata, city files)."""
    f = os.open(path, FILE_FLAGS)
    try:
        return read_bounded(f, path)
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


def expected_runtime(lanes, codex_hooks_sha, settings_sha=None):
    """{path: spec} for every RUNTIME entry the named lanes write, from worker-independent pins."""
    expected = {}
    if not lanes:
        return expected
    for path, (source, mode) in CITY_FILES.items():
        if path == '.gc/settings.json' and settings_sha is not None:
            digest = settings_sha
        else:
            _, data = read_file(source)
            digest = sha256(data)
        expected[path] = dict(kind='file', mode=mode, sha256=digest)
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


def same_walk(before, after):
    return all(set(a) == set(b) and all(stat_key(a[p]) == stat_key(b[p]) for p in a)
               for a, b in zip(before, after))


def tree_digest(root):
    """v3: domain tag, then sorted (kind, UTF-8 path, octal mode, content) length-prefixed fields.

    Every field has an unsigned 8-byte big-endian length. The root is a directory with path '';
    directories have empty content. .git is ordinary skill content. Links and hard links refuse.
    """
    h = hashlib.sha256(b'gct-oak5.skill-tree.v3\0')
    root_stat = os.lstat(root)
    entries, dirs = walk(root, skill=True)
    total = 0
    for path, s in sorted({'': root_stat, **dirs, **entries}.items()):
        if stat.S_ISDIR(s.st_mode):
            kind, data = b'd', b''
        else:
            require(stat.S_ISREG(s.st_mode), 'skill target holds a non-regular entry: %s/%s' % (root, path))
            _, data = read_regular(root, path, s, MAX_TOTAL_BYTES - total)
            total += len(data)
            kind = b'f'
        for field in (kind, path.encode(), format(stat.S_IMODE(s.st_mode), '04o').encode(), data):
            h.update(len(field).to_bytes(8, 'big'))
            h.update(field)
    require(same_walk((entries, dirs), walk(root, skill=True)) and stat_key(os.lstat(root)) == stat_key(root_stat),
            'skill target changed during the export: ' + str(root))
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


def content(worktree, clone, base, lanes, codex_hooks_sha, settings_sha=None):
    """The content part of an image: entries, deleted, ignored, runtime, runtime dir modes."""
    check_clone(clone, base)
    tree = base_tree(clone, base)
    found, dirs = walk(worktree)
    cc = '.claude/.cc-writes'
    require(cc not in found and not any(p.startswith(cc + '/') for p in (*found, *dirs)),
            cc + ' must be an empty directory')
    if cc in dirs:
        require('claude' in lanes and dirs[cc].st_uid == os.getuid()
                and not stat.S_IMODE(dirs[cc].st_mode) & 0o7022, cc + ' has an unsafe lane, owner or mode')
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

    expected = expected_runtime(lanes, codex_hooks_sha, settings_sha)
    runtime, entries, ignored_entries, total = [], [], [], 0

    def read_content(path, before):
        nonlocal total
        result = read_regular(worktree, path, before, MAX_TOTAL_BYTES - total)
        total += len(result[1])
        return result

    def add_row(rows, row):
        require(len(entries) + len(ignored_entries) < MAX_FILES, 'image over the bounds')
        rows.append(row)
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
            st, data = read_content(path, s)
            now = '100755' if st.st_mode & stat.S_IXUSR else '100644'
            if blob_id(data) == oid and now == mode:
                continue
            require(name not in STOP_NAMES, 'stop path changed: ' + path)
            add_row(entries, dict(path=path, status='M', mode=now, blob=blob_id(data), sha256=sha256(data), size=len(data)))
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
                st, data = read_content(path, s)
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
            st, data = read_content(path, s)
            add_row(ignored_entries, dict(path=path, mode=oct(stat.S_IMODE(st.st_mode)), size=len(data), sha256=sha256(data)))
            continue
        require(stat.S_ISREG(s.st_mode), 'new path is not a regular file: ' + path)
        st, data = read_content(path, s)
        now = '100755' if st.st_mode & stat.S_IXUSR else '100644'
        add_row(entries, dict(path=path, status='A', mode=now, blob=blob_id(data), sha256=sha256(data), size=len(data)))
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
    deleted = sorted(p for p in tree if p not in found)
    for path in deleted:
        require(PurePosixPath(path).name not in STOP_NAMES, 'stop path deleted: ' + path)
    require(len(entries) + len(deleted) + len(ignored_entries) <= MAX_FILES and total <= MAX_TOTAL_BYTES,
            'image over the bounds')
    again, again_dirs = walk(worktree)
    require(same_walk((found, dirs), (again, again_dirs)), 'worktree changed during the export')
    return dict(entries=entries, deleted=deleted, ignored=ignored_entries, runtime=runtime, dir_modes=dir_modes)


def packed_refs(data):
    """Strict SHA-1 packed-refs grammar; reject duplicates anywhere, including conflicting values."""
    require(data.endswith(b'\n'), 'packed-refs missing final newline')
    refs, previous, peeled = {}, None, False
    for number, line in enumerate(data.split(b'\n')[:-1]):
        if line.startswith(b'#'):
            require(number == 0 and line.startswith(b'# pack-refs with: '), 'packed-refs invalid header')
            flags = line[len(b'# pack-refs with: '):].split()
            require(len(flags) == len(set(flags)) and set(flags) <= {b'peeled', b'fully-peeled', b'sorted'},
                    'packed-refs invalid header flags')
            continue
        if line.startswith(b'^'):
            require(previous is not None and previous.startswith('refs/tags/') and not peeled
                    and re.fullmatch(rb'\^[0-9a-f]{40}', line), 'packed-refs invalid peeled row')
            peeled = True
            continue
        match = re.fullmatch(rb'([0-9a-f]{40}) (refs/[^\x00-\x20\x7f]+)', line)
        require(match is not None, 'packed-refs malformed row')
        oid, raw_ref = match.groups()
        ref = raw_ref.decode('utf-8')
        require(not any(c in ref for c in '~^:?*[\\') and '..' not in ref and '@{' not in ref
                and not ref.endswith('.')
                and all(part and not part.startswith('.') and not part.endswith('.lock') for part in ref.split('/')),
                'packed-refs malformed ref name')
        require(ref not in refs, 'packed-refs duplicate or conflicting ref: ' + ref)
        refs[ref] = oid.decode()
        previous, peeled = ref, False
    return refs


def branch_ref():
    """A loose ref wins; only a missing loose file permits the strictly parsed packed fallback."""
    ref = 'refs/heads/' + BRANCH
    try:
        _, raw = read_file(CANONICAL_GIT / ref)
    except FileNotFoundError:
        refs = packed_refs(read_file(CANONICAL_GIT / 'packed-refs')[1])
        require(ref in refs, 'packed-refs missing exact handover branch')
        return refs[ref]
    require(re.fullmatch(rb'[0-9a-f]{40}\n', raw), 'malformed loose branch ref')
    return raw.decode().strip()


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
    meta['branch_ref'] = branch_ref()
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
    settings = [r for r in image['runtime'] if r['path'] == '.gc/settings.json']
    settings_sha = None
    if image['lanes']:
        require(len(settings) == 1 and settings[0].get('kind') == 'file' and settings[0].get('mode') == '0o644'
                and re.fullmatch(r'[0-9a-f]{64}', settings[0].get('sha256', '')), 'image settings digest invalid')
        settings_sha = settings[0]['sha256']
    got = content(copy, args.clone, image['base'], image['lanes'], hooks, settings_sha)
    problems = [k for k in ('entries', 'deleted', 'ignored', 'runtime', 'dir_modes') if got[k] != image[k]]
    print(json.dumps(dict(ok=not problems, differs=problems)))
    return 0 if not problems else 1


def holder(args):
    image = load(args.image)
    require(image['lanes'] == STEPS[args.step]['next'], 'holder image lanes do not match step')
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
