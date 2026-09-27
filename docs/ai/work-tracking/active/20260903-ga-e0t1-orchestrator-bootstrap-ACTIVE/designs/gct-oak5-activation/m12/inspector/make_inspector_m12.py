"""Generate the M12 platform inspector from the M11 inspector by count-checked substitutions.

  python3 -I -B make_inspector_m12.py

The M11 inspector (gct-oak5-activation/m11/inspector) refuses any installed manifest but M11 9f60c3bf. M12 (file
114b4a00, gct-oak5 codex choice) is now installed over the same Core 207a78e2, built from f45a6262 (tree f1011ada). So only two
bindings move: the pinned manifest file digest and the build root. The Core source clone, commit and tree are
unchanged. Sources load by digest; any other occurrence count refuses.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
M11 = HERE.parent.parent/'m11'/'inspector'
M11_MANIFEST_FILE = '9f60c3bf69a64e3483b2a069fd542ae4ddefee5c0e63f1bc06a388ab7f59a1be'
M12_MANIFEST_FILE = '114b4a000471ee145d494732db361521ea237b3e4857607b06720b7b105327b9'
ROOT_OLD, ROOT_NEW = '/var/tmp/gct-oak5-platform-inspector-m11-20260927', '/var/tmp/gct-oak5-platform-inspector-m12-20260927'


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
    main = source(M11/'platform-inspect-main.go', MAIN_SHA)
    write('platform-inspect-main.go', substitute(main, [
        ('const want = "%s"' % M11_MANIFEST_FILE, 'const want = "%s"' % M12_MANIFEST_FILE, 1)], 'main.go'))
    builder = source(M11/'inspector-build.py', BUILD_SHA)
    write('inspector-build.py', substitute(builder, [
        ("ROOT = Path('%s')" % ROOT_OLD, "ROOT = Path('%s')" % ROOT_NEW, 1)], 'inspector-build.py'))


MAIN_SHA = '405cbd6fb27a7d8d7e005b69e22aaeeca68f6bda381e088ed19215bb4e5b3903'
BUILD_SHA = 'b77411c1d9650133e729e874face70bb95c51eacb537bc38ae30d293c39f6975'

if __name__ == '__main__':
    if sys.argv[1:]:
        raise SystemExit(__doc__)
    generate()
