"""Generate the ga-bebv S1 custody build from the executed ga-e0t1.18 build by count-checked substitutions.

  python3 -I -B make_s1.py build     s1a: build.py (offline custody build of the 0b63856a tree)

ga-bebv deploys the ga-6umo launch-parameter hotfix: Core PR 49, GitHub merge commit 0b63856a on f3856bd1,
tree f1011ada. The build source is the reviewed branch head f45a6262 itself: it is signed by the operator key
FD5585922F5335BC378AD8D42ECF4432C7E7982D (signing subkey 2ECF4432C7E7982D), passed two independent
round-5 reviews, and its tree f1011ada is byte-identical to the merge commit. No new attestation commit is
made. The build asserts that MAIN's second parent is HEAD, so the built source is exactly the merged head.

Changes from the ga-e0t1.18 build (sha 126ad49d), each asserted to occur exactly once:
- identity: root /var/tmp/ga-bebv-build-20260927, HEAD f45a6262, TREE f1011ada, MAIN 0b63856a, schema;
- the docstring names the new source;
- a new assertion that MAIN^2 is HEAD.
Every other line, including the isolated gc version probe, the audited-input function, the two-clone
reproducibility check and the tool digests, is the executed ga-e0t1.18 code.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = HERE.parent/'ga-e0t1.18-deploy'/'build.py'
SOURCE_SHA = '126ad49d65add2733a79c976005cd5c15e9d01a1ca653d502a0ffba6c5f71a0b'
HEAD = 'f45a626213dc5b8d0b52f097d978cca56e506df0'
TREE = 'f1011adaf673937fbda1d254a53c8f0eadf17c5c'
MAIN = '0b63856a8c14ba25191ee2b338be1ac3f48385f3'
ROOT = '/var/tmp/ga-bebv-build-20260927'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sub(text, old, new, count=1):
    found = text.count(old)
    if found != count:
        raise SystemExit('expected %d occurrence(s) of %r, found %d' % (count, old[:80], found))
    return text.replace(old, new)


def build():
    raw = SOURCE.read_bytes()
    if sha(raw) != SOURCE_SHA:
        raise SystemExit('reviewed source drift: %s' % SOURCE)
    text = raw.decode()
    text = sub(text, '"""Offline reproducible custody build of Core main f3856bd1 (ga-e0t1.18); no installation or live operation.\n',
               '"""Offline reproducible custody build of Core main 0b63856a (ga-bebv); no installation or live operation.\n')
    text = sub(text, 'Source: the locally signed build-source commit deefb98b, whose tree af5c3f04 is byte-identical to the\n'
                     'GitHub merge commit f3856bd1 (Core PR 48 on b6843d3f, the live build tree c9f19d21). Two fresh\n',
               'Source: the operator-signed reviewed head f45a6262, whose tree f1011ada is byte-identical to the\n'
               'GitHub merge commit 0b63856a (Core PR 49 on f3856bd1, the live build tree af5c3f04). Two fresh\n')
    text = sub(text, "ROOT = Path('/var/tmp/ga-e0t1.18-build-20260926')", "ROOT = Path('%s')" % ROOT)
    text = sub(text, "HEAD = 'deefb98b2aed07875df31351d081fbac195cb1cd'", "HEAD = '%s'" % HEAD)
    text = sub(text, "TREE = 'af5c3f045c1f50cd62c859f6dc58fa613e5f2f99'", "TREE = '%s'" % TREE)
    text = sub(text, "MAIN = 'f3856bd146995305c0c2b5f958390b3760b01e21'", "MAIN = '%s'" % MAIN)
    text = sub(text, "    run('verify-head', git + ['-C', str(RIG), 'verify-commit', HEAD], ROOT)\n",
               "    assert run('rig-main-head-parent', git + ['-C', str(RIG), 'rev-parse', MAIN + '^2'],\n"
               "               ROOT).decode().strip() == HEAD, 'MAIN is not the merge of HEAD'\n"
               "    run('verify-head', git + ['-C', str(RIG), 'verify-commit', HEAD], ROOT)\n")
    text = sub(text, "'schema': 'ga-e0t1.18.build.v1'", "'schema': 'ga-bebv.build.v1'")
    out = HERE/'build.py'
    out.write_bytes(text.encode())
    out.chmod(0o644)
    print('build.py', sha(text.encode()))


if __name__ == '__main__':
    if sys.argv[1:] == ['build']:
        build()
    else:
        raise SystemExit(__doc__)
