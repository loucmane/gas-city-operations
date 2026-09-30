"""Count-checked rebind of the reviewed M12 observational build recipe.

No product source, runtime, installed manifest, or historical build is changed.
Generated files are create-only. Building does not execute the inspector.
"""
import hashlib
from pathlib import Path

HERE = Path(__file__).parent
OLD = HERE.parent.parent / 'gct-oak5-activation/m12/inspector'
MANIFEST = 'd02a3adbd044ebaf4f1dd4606c0af5dea50bcab4bca5efb2f3da5aab14e68481'


def source(name, pin):
    raw = (OLD / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pin
    return raw.decode()


def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def main():
    entry = source('platform-inspect-main.go', '367056c801f85a4409589d231a0e91243f7ed1d9c6ded9a2e658865c8e3b0ad4')
    entry = replace(entry, '114b4a000471ee145d494732db361521ea237b3e4857607b06720b7b105327b9', MANIFEST)
    builder = source('inspector-build.py', '95ec28c56c98ed9613d27bba525fe00af319863ae33d16743d3cfb29d4352ec8')
    end = builder.index('"""', 3) + 3
    builder = '"""Build the exact M15 observer from adopted Core in a fresh private root.\n\nNo live installation or inspector execution. Offline existing dependencies only.\n"""' + builder[end:]
    for old, new in (
        ('/var/tmp/gct-oak5-platform-inspector-m12-20260927', '/var/tmp/ga-mb91-platform-inspector-m15-20260930-r1'),
        ('/var/tmp/ga-bebv-build-20260927/repro-source', '/var/tmp/ga-e0t1.22-custody-build-20260930-r1/repro-source'),
        ('f45a626213dc5b8d0b52f097d978cca56e506df0', '53f2e232da03a1e176cf64cf4fe1aa9c3f3beb6b'),
        ('f1011adaf673937fbda1d254a53c8f0eadf17c5c', '2a253aabadc432c3c9f8953961b7a0db96291191'),
        ("'USER': 'loucmane'}", "'USER': 'loucmane', 'GOCACHE': str(ROOT / 'go-cache')}"),
        ('                  executed=False, installed=False)',
         '                  manifest_sha256=' + repr(MANIFEST) + ',\n                  executed=False, installed=False)'),
    ):
        builder = replace(builder, old, new)
    for name, text in (('platform-inspect-main.go', entry), ('inspector-build.py', builder)):
        raw = text.encode()
        with (HERE / name).open('xb') as stream:
            stream.write(raw)
        print(name, hashlib.sha256(raw).hexdigest())


if __name__ == '__main__':
    main()
