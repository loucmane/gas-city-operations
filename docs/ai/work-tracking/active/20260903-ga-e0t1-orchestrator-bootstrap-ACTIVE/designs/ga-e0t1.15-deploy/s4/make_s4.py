"""Generate the ga-e0t1.15 S4 acceptance-window package from reviewed sources by count-checked substitutions.

  python3 -I -B make_s4.py inspector     phase 1: the platform inspector, rebound to Core 9faeabc2 and the M6 manifest

Every source is loaded by its reviewed digest. Every substitution names the exact text it replaces and how many
times it must occur; generation refuses on any other count. Generated files are written beside this generator.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
DESIGNS = HERE.parent.parent
Z38 = DESIGNS/'ga-4z38-window'/'inspector'
CORE_OLD, CORE_NEW = '796d9a7a67c42294fdc467c107bb59b76e482301', '9faeabc2892d8c7133111e13ad55af66790a2ac6'
TREE_OLD, TREE_NEW = 'f2c120a5ac9ea25ebc395c1b3cfa4eb30dcafd13', 'c9f19d215d271a5dda0bce296dc72c32dfc35499'
M5_MANIFEST_FILE = '2d7eadce62c4e567697813cc9122414f1e94c3bd9d389aef92015adef7f36319'
M6_MANIFEST_FILE = '7f335ad83091a1a907b628fa5813c7daf6a530340a2ed404476797b5db90fefb'
INSPECTOR_ROOT = '/var/tmp/ga-e0t1.15-platform-inspector-20260925'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source(path, digest):
    raw = Path(path).read_bytes()
    if sha(raw) != digest:
        raise SystemExit('reviewed source drift: %s' % path)
    return raw.decode()


def substitute(text, substitutions, name):
    for old, new, count in substitutions:
        found = text.count(old)
        if found != count:
            raise SystemExit('%s: expected %d occurrence(s) of %r, found %d' % (name, count, old[:80], found))
        text = text.replace(old, new)
    return text


def write(name, text):
    path = HERE/name
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode() if isinstance(text, str) else text
    path.write_bytes(data)
    path.chmod(0o644)
    print(name, sha(data))
    return sha(data)


def inspector():
    main = source(Z38/'platform-inspect-main.go', 'e5e9872f2b57d70c9fbde8e3d152978eaf9266453af67dbd1a82a4d1886b7ca3')
    main = substitute(main, [
        # The inspector refuses any manifest but the pinned one; M6 is now installed.
        ('const want = "%s"' % M5_MANIFEST_FILE, 'const want = "%s"' % M6_MANIFEST_FILE, 1),
    ], 'platform-inspect-main.go')
    write('inspector/platform-inspect-main.go', main)
    builder = source(Z38/'inspector-build-r1.py', 'aba0868b000425df39dfbeaf48f70d15366958d532c3df264bf2cd0e69fde20a')
    builder = substitute(builder, [
        ("ROOT = Path('/var/tmp/ga-4z38-platform-inspector-20260924-r1')", "ROOT = Path('%s')" % INSPECTOR_ROOT, 1),
        # The S1 reproduction clone of the build source 9faeabc2 (tree c9f19d21), not a live repository.
        ("CORE = '/home/loucmane/gascity-core-worktrees/ga-ecwh-typed-worker-receipts'",
         "CORE = '/var/tmp/ga-e0t1.15-build-20260925/repro-source'", 1),
        ("CORE_COMMIT = '%s'" % CORE_OLD, "CORE_COMMIT = '%s'" % CORE_NEW, 1),
        ("CORE_TREE = '%s'" % TREE_OLD, "CORE_TREE = '%s'" % TREE_NEW, 1),
    ], 'inspector-build-r1.py')
    write('inspector/inspector-build-s4.py', builder)


if __name__ == '__main__':
    if sys.argv[1:] == ['inspector']:
        inspector()
    else:
        raise SystemExit(__doc__)
