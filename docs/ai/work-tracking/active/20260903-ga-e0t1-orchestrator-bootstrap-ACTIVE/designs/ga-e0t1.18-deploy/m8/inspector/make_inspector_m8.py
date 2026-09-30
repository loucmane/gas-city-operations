"""Generate the M8 platform inspector from the reviewed M7 inspector by count-checked substitutions.

  python3 -I -B make_inspector_m8.py

The M7 inspector (designs/ga-e0t1.18-deploy/inspector, reviewed at bd4931db) refuses any installed manifest but
M7 4bec5ef1. M8 (file 63820eac) is now installed over the same Core deefb98b, so exactly two bindings move: the
pinned manifest file digest and the build root. Sources load by digest; any other occurrence count refuses.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
M7 = HERE.parent.parent/'inspector'
M7_MANIFEST_FILE = '4bec5ef14bd81f6dc1830ada48fc502937ff91a531981dfff3fde5aaa92a9759'
M8_MANIFEST_FILE = '63820eacf37a46ec6d6d97cfe0434189a2a41a27c6650462b992d1034da183b8'
ROOT_OLD, ROOT_NEW = '/var/tmp/ga-e0t1.18-platform-inspector-20260926', '/var/tmp/ga-e0t1.18-platform-inspector-m8-20260926'


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
    main = source(M7/'platform-inspect-main.go', '115835c04eb6207bb22adaaaddafaeea8c061447c3f56e56f8b6bc1d7cc4da5d')
    write('platform-inspect-main.go', substitute(main, [
        ('const want = "%s"' % M7_MANIFEST_FILE, 'const want = "%s"' % M8_MANIFEST_FILE, 1)], 'main.go'))
    builder = source(M7/'inspector-build.py', '49deb5545c31d9d6fbd7d55dbc784575025cda351f0a0a077dc01713fd1af4a1')
    write('inspector-build.py', substitute(builder, [
        ("ROOT = Path('%s')" % ROOT_OLD, "ROOT = Path('%s')" % ROOT_NEW, 1)], 'inspector-build.py'))


if __name__ == '__main__':
    if sys.argv[1:]:
        raise SystemExit(__doc__)
    generate()
