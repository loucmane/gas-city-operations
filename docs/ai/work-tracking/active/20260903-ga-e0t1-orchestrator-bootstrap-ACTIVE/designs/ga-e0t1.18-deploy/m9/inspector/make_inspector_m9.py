"""Generate the M9 platform inspector from the M8 inspector by count-checked substitutions.

  python3 -I -B make_inspector_m9.py

The M8 inspector (m8/inspector, rebound from the reviewed M7 inspector) refuses any installed manifest but
M8 63820eac. M9 (file 5a29dc59) is now installed over the same Core deefb98b, so exactly two bindings move: the
pinned manifest file digest and the build root. Sources load by digest; any other occurrence count refuses.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
M8 = HERE.parent.parent/'m8'/'inspector'
M8_MANIFEST_FILE = '63820eacf37a46ec6d6d97cfe0434189a2a41a27c6650462b992d1034da183b8'
M9_MANIFEST_FILE = '5a29dc596af192e0f314391453d25d6be548695a0defd64bdfc2fa76554e4993'
ROOT_OLD, ROOT_NEW = '/var/tmp/ga-e0t1.18-platform-inspector-m8-20260926', '/var/tmp/ga-e0t1.18-platform-inspector-m9-20260926'


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
    main = source(M8/'platform-inspect-main.go', '29e16c0ebad6de00f1dd6058eb29751a0bcee3791decad7eb35a540be83e99cb')
    write('platform-inspect-main.go', substitute(main, [
        ('const want = "%s"' % M8_MANIFEST_FILE, 'const want = "%s"' % M9_MANIFEST_FILE, 1)], 'main.go'))
    builder = source(M8/'inspector-build.py', 'ec87ed9669b81bb9a1cad80532d86484d9cf60390cd9644b543822ac68bc9f91')
    write('inspector-build.py', substitute(builder, [
        ("ROOT = Path('%s')" % ROOT_OLD, "ROOT = Path('%s')" % ROOT_NEW, 1)], 'inspector-build.py'))


if __name__ == '__main__':
    if sys.argv[1:]:
        raise SystemExit(__doc__)
    generate()
