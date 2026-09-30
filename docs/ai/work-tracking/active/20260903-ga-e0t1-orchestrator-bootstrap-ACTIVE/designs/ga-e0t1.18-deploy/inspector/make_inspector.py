"""Generate the ga-e0t1.18 platform inspector from the reviewed S4 inspector by count-checked substitutions.

  python3 -I -B make_inspector.py

The S4 inspector (designs/ga-e0t1.15-deploy/s4/inspector) refuses any installed manifest but M6 7f335ad8 and was
built from Core 9faeabc2. M7 (manifest file 4bec5ef1) is now installed for Core deefb98b, so exactly these
bindings move: the pinned manifest file digest, the build root, the S1 reproduction clone, the Core commit and
its tree. Every source is loaded by its reviewed digest; generation refuses on any other occurrence count.
Generated files are written beside this generator.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
S4 = HERE.parent.parent/'ga-e0t1.15-deploy'/'s4'/'inspector'
CORE_OLD, CORE_NEW = '9faeabc2892d8c7133111e13ad55af66790a2ac6', 'deefb98b2aed07875df31351d081fbac195cb1cd'
TREE_OLD, TREE_NEW = 'c9f19d215d271a5dda0bce296dc72c32dfc35499', 'af5c3f045c1f50cd62c859f6dc58fa613e5f2f99'
M6_MANIFEST_FILE = '7f335ad83091a1a907b628fa5813c7daf6a530340a2ed404476797b5db90fefb'
M7_MANIFEST_FILE = '4bec5ef14bd81f6dc1830ada48fc502937ff91a531981dfff3fde5aaa92a9759'
ROOT_OLD, ROOT_NEW = '/var/tmp/ga-e0t1.15-platform-inspector-20260925', '/var/tmp/ga-e0t1.18-platform-inspector-20260926'
REPRO_OLD, REPRO_NEW = '/var/tmp/ga-e0t1.15-build-20260925/repro-source', '/var/tmp/ga-e0t1.18-build-20260926/repro-source'


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
    data = text.encode() if isinstance(text, str) else text
    path.write_bytes(data)
    path.chmod(0o644)
    print(name, sha(data))
    return sha(data)


def generate():
    main = source(S4/'platform-inspect-main.go', '585e0d376d90a26cab57d6e676d4aa3567df53b4c8b10816e8fac8071901a7f7')
    main = substitute(main, [
        # The inspector refuses any manifest but the pinned one; M7 is now installed.
        ('const want = "%s"' % M6_MANIFEST_FILE, 'const want = "%s"' % M7_MANIFEST_FILE, 1),
    ], 'platform-inspect-main.go')
    write('platform-inspect-main.go', main)
    builder = source(S4/'inspector-build-s4.py', '0fcf139cfe977f07313adb6aa148646ebf1aa4930b0ad80a545f6dbb240c73bc')
    builder = substitute(builder, [
        ("ROOT = Path('%s')" % ROOT_OLD, "ROOT = Path('%s')" % ROOT_NEW, 1),
        # The S1 reproduction clone of the build source deefb98b (tree af5c3f04), not a live repository.
        ("CORE = '%s'" % REPRO_OLD, "CORE = '%s'" % REPRO_NEW, 1),
        ("CORE_COMMIT = '%s'" % CORE_OLD, "CORE_COMMIT = '%s'" % CORE_NEW, 1),
        ("CORE_TREE = '%s'" % TREE_OLD, "CORE_TREE = '%s'" % TREE_NEW, 1),
    ], 'inspector-build-s4.py')
    write('inspector-build.py', builder)


if __name__ == '__main__':
    if sys.argv[1:]:
        raise SystemExit(__doc__)
    generate()
