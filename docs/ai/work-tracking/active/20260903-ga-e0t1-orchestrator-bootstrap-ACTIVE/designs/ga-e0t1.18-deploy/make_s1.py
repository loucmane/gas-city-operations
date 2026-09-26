"""Generate the ga-e0t1.18 S1 custody build from the reviewed ga-e0t1.15 build by count-checked substitutions.

  python3 -I -B make_s1.py build     s1a: build.py (offline custody build of the f3856bd1 tree)

ga-e0t1.18 deploys Core PR 48 (merge f3856bd1, tree af5c3f04 = the managed-signed commit 0e638e1f on base
b6843d3f). The build source is the locally signed attestation deefb98b (tree af5c3f04, parents b6843d3f and
0e638e1f, signed by the operator key FD5585922F5335BC378AD8D42ECF4432C7E7982D, branch
codex/ga-e0t1.18-build-source in the rig repository), made exactly as 9faeabc2 was for ga-e0t1.15.

Changes from the ga-e0t1.15 build (sha dd51fe22), each asserted to occur exactly once:
- identity: root /var/tmp/ga-e0t1.18-build-20260926, HEAD deefb98b, TREE af5c3f04, MAIN f3856bd1, schema;
- the post-build `gc version --json` probe runs with an isolated HOME and GC_HOME under the build root, plus
  DO_NOT_TRACK=1 and GC_DISABLE_USAGE_METRICS=1. In ga-e0t1.15 the same probe ran with the operator HOME and
  rewrote the live city shim .gc/scripts/gc-beads-bd.sh (PLAN.md S1 correction r3); this removes that path.
Every other line, including the audited-input function, the two-clone reproducibility check and the tool
digests, is the reviewed ga-e0t1.15 code.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = HERE.parent/'ga-e0t1.15-deploy'/'build.py'
SOURCE_SHA = 'dd51fe2295a49f6f6cd5ef0a768e2e77c512982527406acbbde29717d099db60'
HEAD = 'deefb98b2aed07875df31351d081fbac195cb1cd'
TREE = 'af5c3f045c1f50cd62c859f6dc58fa613e5f2f99'
MAIN = 'f3856bd146995305c0c2b5f958390b3760b01e21'
ROOT = '/var/tmp/ga-e0t1.18-build-20260926'


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
    text = sub(text, '"""Offline reproducible custody build of Core main b6843d3f (ga-e0t1.15); no installation or live operation.\n',
               '"""Offline reproducible custody build of Core main f3856bd1 (ga-e0t1.18); no installation or live operation.\n')
    text = sub(text, 'Source: the locally signed build-source commit 9faeabc2, whose tree c9f19d21 is byte-identical to the\n'
                     'GitHub merge commit b6843d3f (Core PRs 46 and 47 on e6366b9e, the live tree f2c120a5). Two fresh\n',
               'Source: the locally signed build-source commit deefb98b, whose tree af5c3f04 is byte-identical to the\n'
               'GitHub merge commit f3856bd1 (Core PR 48 on b6843d3f, the live build tree c9f19d21). Two fresh\n')
    text = sub(text, "ROOT = Path('/var/tmp/ga-e0t1.15-build-20260925')", "ROOT = Path('%s')" % ROOT)
    text = sub(text, "HEAD = '9faeabc2892d8c7133111e13ad55af66790a2ac6'", "HEAD = '%s'" % HEAD)
    text = sub(text, "TREE = 'c9f19d215d271a5dda0bce296dc72c32dfc35499'", "TREE = '%s'" % TREE)
    text = sub(text, "MAIN = 'b6843d3f539eeebaf9d9c12e7d095d25cdee585d'", "MAIN = '%s'" % MAIN)
    text = sub(text, "SOURCES = [('a', 'repro-source'), ('b', 'repro-source-b')]\n",
               "SOURCES = [('a', 'repro-source'), ('b', 'repro-source-b')]\n"
               "# ga-e0t1.18: the gc version probe must never see the operator HOME or GC_HOME: with them its config\n"
               "# load repairs the registered live city's runtime assets (ga-e0t1.15 PLAN.md S1 correction r3).\n"
               "PROBE_ENV = dict(ENV, HOME=str(ROOT / 'probe-home'), GC_HOME=str(ROOT / 'probe-gc-home'),\n"
               "                 DO_NOT_TRACK='1', GC_DISABLE_USAGE_METRICS='1')\n")
    text = sub(text, "    (ROOT / 'tmp').mkdir(mode=0o700)\n",
               "    (ROOT / 'tmp').mkdir(mode=0o700)\n"
               "    (ROOT / 'probe-home').mkdir(mode=0o700)\n"
               "    (ROOT / 'probe-gc-home').mkdir(mode=0o700)\n")
    text = sub(text, "        parsed = json.loads(run('version-' + tag, [str(output), 'version', '--json'], ROOT))\n",
               "        parsed = json.loads(run('version-' + tag, [str(output), 'version', '--json'], ROOT, PROBE_ENV))\n")
    text = sub(text, "'schema': 'ga-e0t1.15.build.v1'", "'schema': 'ga-e0t1.18.build.v1'")
    out = HERE/'build.py'
    out.write_bytes(text.encode())
    out.chmod(0o644)
    print('build.py', sha(text.encode()))


if __name__ == '__main__':
    if sys.argv[1:] == ['build']:
        build()
    else:
        raise SystemExit(__doc__)
