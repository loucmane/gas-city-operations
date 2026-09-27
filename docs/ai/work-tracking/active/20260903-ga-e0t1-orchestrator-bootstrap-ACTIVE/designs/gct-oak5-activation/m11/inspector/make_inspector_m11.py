"""Generate the M11 platform inspector from the M10 inspector by count-checked substitutions.

  python3 -I -B make_inspector_m11.py

The M10 inspector (ga-bebv-deploy/m10/inspector) refuses any installed manifest but M10 2b902a83. M11 (file
9f60c3bf, gct-oak5) is now installed over the same Core 207a78e2, built from f45a6262 (tree f1011ada). So only two
bindings move: the pinned manifest file digest and the build root. The Core source clone, commit and tree are
unchanged. Sources load by digest; any other occurrence count refuses.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
M10 = HERE.parent.parent.parent/'ga-bebv-deploy'/'m10'/'inspector'
M10_MANIFEST_FILE = '2b902a83577acf71f9dd93a97d43d8478f7c4b291b0992e8ba5a5e44fe66f7f2'
M11_MANIFEST_FILE = '9f60c3bf69a64e3483b2a069fd542ae4ddefee5c0e63f1bc06a388ab7f59a1be'
ROOT_OLD, ROOT_NEW = '/var/tmp/ga-bebv-platform-inspector-m10-20260927', '/var/tmp/gct-oak5-platform-inspector-m11-20260927'


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
    main = source(M10/'platform-inspect-main.go', MAIN_SHA)
    write('platform-inspect-main.go', substitute(main, [
        ('const want = "%s"' % M10_MANIFEST_FILE, 'const want = "%s"' % M11_MANIFEST_FILE, 1)], 'main.go'))
    builder = source(M10/'inspector-build.py', BUILD_SHA)
    write('inspector-build.py', substitute(builder, [
        ("ROOT = Path('%s')" % ROOT_OLD, "ROOT = Path('%s')" % ROOT_NEW, 1)], 'inspector-build.py'))


MAIN_SHA = '1f87b7b86afc322c385aed0dbc22491b511b6704f07bb5e9078f342aff7d0e3a'
BUILD_SHA = '88c370d7394cef533d716938124000f4a2818924b0c40098c903d5a159685d6d'

if __name__ == '__main__':
    if sys.argv[1:]:
        raise SystemExit(__doc__)
    generate()
