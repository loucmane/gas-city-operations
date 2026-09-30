"""Generate the M10 platform inspector from the M9 inspector by count-checked substitutions.

  python3 -I -B make_inspector_m10.py

The M9 inspector (ga-e0t1.18-deploy/m9/inspector) refuses any installed manifest but M9 5a29dc59 and builds
against Core deefb98b. M10 (file 2b902a83) is now installed over Core 207a78e2, built from f45a6262 (tree
f1011ada). So four bindings move: the pinned manifest file digest, the build root, and the Core source clone,
commit and tree (the sequence 16 reproduction clone /var/tmp/ga-bebv-build-20260927/repro-source). Sources
load by digest; any other occurrence count refuses.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
M9 = HERE.parent.parent.parent/'ga-e0t1.18-deploy'/'m9'/'inspector'
M9_MANIFEST_FILE = '5a29dc596af192e0f314391453d25d6be548695a0defd64bdfc2fa76554e4993'
M10_MANIFEST_FILE = '2b902a83577acf71f9dd93a97d43d8478f7c4b291b0992e8ba5a5e44fe66f7f2'
ROOT_OLD, ROOT_NEW = '/var/tmp/ga-e0t1.18-platform-inspector-m9-20260926', '/var/tmp/ga-bebv-platform-inspector-m10-20260927'
CORE_OLD, CORE_NEW = '/var/tmp/ga-e0t1.18-build-20260926/repro-source', '/var/tmp/ga-bebv-build-20260927/repro-source'
COMMIT_OLD, COMMIT_NEW = 'deefb98b2aed07875df31351d081fbac195cb1cd', 'f45a626213dc5b8d0b52f097d978cca56e506df0'
TREE_OLD, TREE_NEW = 'af5c3f045c1f50cd62c859f6dc58fa613e5f2f99', 'f1011adaf673937fbda1d254a53c8f0eadf17c5c'


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
    data = text.encode()
    path.write_bytes(data)
    path.chmod(0o644)
    print(name, sha(data))


def generate():
    main = source(M9/'platform-inspect-main.go', '1fa212cead41bbdb998ec24146d119b69edb9c5a446f8a9ac1ea9ad50af7b3a5')
    write('platform-inspect-main.go', substitute(main, [
        ('const want = "%s"' % M9_MANIFEST_FILE, 'const want = "%s"' % M10_MANIFEST_FILE, 1)], 'main.go'))
    builder = source(M9/'inspector-build.py', '30e5eb549fb20ab2b17a0e8f93f1ccb98e1468a4c72d2b3bbda253ef8d865501')
    write('inspector-build.py', substitute(builder, [
        ("ROOT = Path('%s')" % ROOT_OLD, "ROOT = Path('%s')" % ROOT_NEW, 1),
        ("CORE = '%s'" % CORE_OLD, "CORE = '%s'" % CORE_NEW, 1),
        ("CORE_COMMIT = '%s'" % COMMIT_OLD, "CORE_COMMIT = '%s'" % COMMIT_NEW, 1),
        ("CORE_TREE = '%s'" % TREE_OLD, "CORE_TREE = '%s'" % TREE_NEW, 1)], 'inspector-build.py'))


if __name__ == '__main__':
    if sys.argv[1:]:
        raise SystemExit(__doc__)
    generate()
