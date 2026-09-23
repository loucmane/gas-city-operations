"""P6 step 1: observe the running revision and derive the receipt input. Read-only except its own records.

The native cycle trace is read (`gc trace show`, a supported read). The live signing
worker's `--version` proves the dependency version it will report. The installed
receipt `01ed1bce` minus its three generated fields then becomes the input draft. Only
these fields change, and each requires its exact predecessor:

- template_commit and member_heads[template]: ff683ed6 -> 28539934;
- permission_revision: the traced running revision, which must differ from ebeefe97,
  since the M5 city edits changed the config;
- profiles[0].provider.version: b7fee446 -> f36deb20;
- profiles[0].argv: the value after --model, claude-opus-5 -> claude-opus-5-5.

No constant waits for M5. `m5_acceptance()` verifies M5's own reviewed records at run
time. It refuses unless all of these hold:

- a COMMIT_PASS review record with two distinct provenance files;
- the committed acceptance that record binds;
- restoration completed;
- the M5 release manifest names Template 28539934 and succeeds R9;
- the live metadata pair is byte-identical to the accepted pair.

  python3 -I -S -B source-launch.py p6-input.py <own sha256>
"""
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types

HERE = Path(__file__).parent
ROOT = Path('/var/tmp/gct-m1wh-p6-input-20260923-r1')
CITY = Path('/home/loucmane/gascity/city')
RECEIPT = CITY/'.gc/runtime/provisioning/receipt.json'
WORKER = Path('/home/loucmane/gas-city-template/bin/gct-claude-signing-worker')
OBS = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/'
           '20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/reports/ga-e0t1.14-rollout-r1/package-r4/resume-r4b/'
           'recovery-source-r2/observe_recovery.py')
OBS_SHA = 'f5357d222f0a2f7ceb9e1a830533f20a4868fe5f3beb247de335843b730bdd78'
GC_SHA = '69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9'
CORE = '796d9a7a67c42294fdc467c107bb59b76e482301'
RECEIPT_OLD_SHA = '01ed1bce0b99d5c6043804cdacb2b25bc725bffb00dba3450888284e570d0a8a'
TEMPLATE_OLD, TEMPLATE_NEW = 'ff683ed6506bdbc38f21f66a1a7f3ce31bdcaa7c', '28539934fa742056e0a65710d5638ff559a21175'
REVISION_OLD = 'ebeefe97a230678b812b164096ec7fccf1c1f2516d8c96ef546c92bcd645acc1'
VERSION_OLD = 'gct-claude-signing-worker 1 dependencies_sha256=b7fee4467e83c7c9d07c2c421142f20297ad1cd3de93192713400aa01d8714b0'
VERSION_NEW = 'gct-claude-signing-worker 1 dependencies_sha256=f36deb20efa5cc11781f1d9703b8e5e0d7897c6357260dff1045bcd86489ff34'
MODEL_OLD, MODEL_NEW = 'claude-opus-5', 'claude-opus-5-5'
M5 = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m5/q')
M5_RELEASE = 'template-pr69-opus55-metadata-m5-20260923'
M5_AUTHORITY = ('template-pr69-authority', '/home/loucmane/gas-city-template-worktrees/gct-m1wh-pr69-authority',
                TEMPLATE_NEW)
# The succession link is previous_metadata.manifest_sha256, the R9 canonical FILE digest. The top-level
# previous_sha256 is the previous Core binary (gc 69d00186) and is not a manifest link.
R9_MANIFEST_FILE = 'a6324753cb238f8de5ed3af72eef9e3a425ab491dae62778f462849814eb1852'
GENERATED = ('canary_runner', 'receipt_sha256')
ENV = dict(HOME='/home/loucmane', USER='loucmane', LOGNAME='loucmane',
           PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin', XDG_RUNTIME_DIR='/run/user/1000',
           DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus', GC_HOME='/home/loucmane/gascity/home',
           GIT_OPTIONAL_LOCKS='0', LC_ALL='C.UTF-8', PYTHONDONTWRITEBYTECODE='1', DO_NOT_TRACK='1')


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def read(path, expected=None):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == 1000 and before.st_nlink == 1,
                'file authority: ' + str(path))
        chunks = []
        while chunk := os.read(fd, 1048576):
            chunks.append(chunk)
        raw = b''.join(chunks)
        require(before == os.fstat(fd) and len(raw) == before.st_size, 'file changed during read: ' + str(path))
    finally:
        os.close(fd)
    require(expected is None or hashlib.sha256(raw).hexdigest() == expected, 'digest drift: ' + str(path))
    return raw


def write(name, value):
    raw = value if isinstance(value, bytes) else (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    fd = os.open(ROOT/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def observer():
    raw = read(OBS, OBS_SHA)
    value = types.ModuleType('observe_recovery'); value.__file__ = str(OBS)
    exec(compile(raw, str(OBS), 'exec', dont_inherit=True), value.__dict__)
    value.GC_SHA = GC_SHA
    return value


def serialize(draft):
    return (json.dumps(draft, indent=2, sort_keys=True) + '\n').encode()


def derive(receipt, revision):
    """Pure: the receipt input for the M5 state, with every predecessor asserted."""
    draft = copy.deepcopy(receipt)
    for key in GENERATED:
        require(key in draft, 'generated field missing: ' + key)
        draft.pop(key)
    require(len(draft['profiles']) == 1, 'profile cardinality')
    profile = draft['profiles'][0]
    require('worker_profile_sha256' in profile, 'generated profile digest missing')
    profile.pop('worker_profile_sha256')
    require(draft['template_commit'] == TEMPLATE_OLD, 'template predecessor')
    draft['template_commit'] = TEMPLATE_NEW
    heads = [h for h in draft['member_heads'] if h['name'] == 'template']
    require(len(heads) == 1 and heads[0]['commit'] == TEMPLATE_OLD, 'template member head predecessor')
    heads[0]['commit'] = TEMPLATE_NEW
    require(draft['permission_revision'] == REVISION_OLD and revision != REVISION_OLD
            and len(revision) == 64 and all(c in '0123456789abcdef' for c in revision), 'revision predecessor')
    draft['permission_revision'] = revision
    require(profile['provider']['version'] == VERSION_OLD, 'provider version predecessor')
    profile['provider']['version'] = VERSION_NEW
    argv = profile['argv']
    positions = [i for i, token in enumerate(argv) if token == '--model']
    require(len(positions) == 1 and argv[positions[0] + 1] == MODEL_OLD, 'argv model predecessor')
    argv[positions[0] + 1] = MODEL_NEW
    require(MODEL_OLD not in argv, 'stale model token')
    return draft


def proven_draft(root=None):
    """For later P6 steps: the recorded draft must be exactly derive() of the preserved
    old receipt and the recorded revision. Independent of the live receipt."""
    root = ROOT if root is None else root
    result = json.loads(read(root/'result.json'))
    require(result['ok'] is True and result['receipt_before_sha256'] == RECEIPT_OLD_SHA, 'input result')
    revision = json.loads(read(root/'revision.json', result['revision_sha256']))
    require(revision['config_revision'] == result['permission_revision'], 'input revision record')
    receipt = json.loads(read(root/'receipt.before.json', RECEIPT_OLD_SHA))
    raw = read(root/'receipt.input.draft.json', result['draft_sha256'])
    require(raw == serialize(derive(receipt, revision['config_revision'])), 'draft is not the reviewed derivation')
    return dict(path=root/'receipt.input.draft.json', raw=raw, sha256=result['draft_sha256'],
                revision=revision['config_revision'], m5=result['m5'])


def m5_acceptance():
    """The M5 committed pair, proven only from M5 reviewed records and the live files."""
    record = json.loads(read(M5/'commit-pass.json'))
    require(set(record) == {'verdict', 'bindings', 'reviewers'} and record['verdict'] == 'COMMIT_PASS'
            and set(record['bindings']) == {'package_sha256', 'acceptance_sha256'}, 'M5 commit review record')
    people = record['reviewers']
    require(len(people) == 2 and len({p['reviewer_id'] for p in people}) == 2, 'two distinct M5 commit reviews')
    seen = set()
    for person in people:
        require(set(person) == {'reviewer_id', 'provenance_path', 'provenance_sha256'}, 'M5 review provenance')
        raw = read(Path(person['provenance_path']), person['provenance_sha256'])
        info = os.stat(person['provenance_path'], follow_symlinks=False)
        proof = json.loads(raw)
        require(set(proof) == {'reviewer_id', 'verdict', 'bindings', 'assessment'}
                and proof['reviewer_id'] == person['reviewer_id'] and proof['verdict'] == 'COMMIT_PASS'
                and proof['bindings'] == record['bindings'] and isinstance(proof['assessment'], str)
                and proof['assessment'].strip(), 'M5 review content')
        seen |= {('path', person['provenance_path']), ('sha', person['provenance_sha256']),
                 ('inode', info.st_dev, info.st_ino)}
    require(len(seen) == 6, 'duplicate M5 review provenance')
    package = record['bindings']['package_sha256']
    acceptance = json.loads(read(M5/'committed-acceptance.json', record['bindings']['acceptance_sha256']))
    require(acceptance['ok'] is True and acceptance['lease_expired'] is True
            and acceptance['package_sha256'] == package, 'M5 acceptance')
    restored = json.loads(read(M5/'restored.json'))
    require(restored['ok'] is True and restored['accepted'] is True, 'M5 restoration')
    manifest = json.loads(read(M5/'manifest.json'))
    last = manifest['integrity']['repositories'][-1]
    require(manifest['release_id'] == M5_RELEASE
            and manifest['previous_metadata']['manifest_sha256'] == R9_MANIFEST_FILE
            and manifest['manifest_sha256'] == acceptance['manifest_sha256']
            and (last['name'], last['path'], last['commit']) == M5_AUTHORITY, 'M5 release binding')
    read(CITY/'.gc/platform/install-manifest.json', acceptance['canonical_file_sha256'])
    read(CITY/'.gc/platform/install-receipt.json', acceptance['receipt_file_sha256'])
    return dict(package_sha256=package, acceptance_path=str(M5/'committed-acceptance.json'),
                acceptance_sha256=record['bindings']['acceptance_sha256'],
                manifest_sha256=acceptance['manifest_sha256'], receipt_sha256=acceptance['receipt_sha256'],
                canonical_file_sha256=acceptance['canonical_file_sha256'],
                receipt_file_sha256=acceptance['receipt_file_sha256'])


def latest_cycle(records, pid):
    require(records, 'no controller cycle in the trace window')
    latest = max(records, key=lambda item: item['seq'])
    require(latest['controller_pid'] == pid and latest['gc_commit'] == CORE
            and latest['completion_status'] == 'completed', 'live controller cycle drift')
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(latest['ts'].replace('Z', '+00:00'))).total_seconds()
    require(0 <= age <= 120 and latest['fields']['active_template_count'] == 0, 'stale or active controller cycle')
    return latest


def main():
    require(globals().get('_SOURCE_SHA') and read(Path(__file__), _SOURCE_SHA), 'source-bound entry required')
    require(len(sys.argv) == 1, 'no arguments')
    require(not os.path.lexists(ROOT), 'input root consumed')
    m5 = m5_acceptance()
    receipt_raw = read(RECEIPT, RECEIPT_OLD_SHA)
    receipt = json.loads(receipt_raw)
    o = observer()
    host = o.host_observation()
    version = subprocess.run([str(WORKER), '--version'], env=ENV, cwd='/', stdin=subprocess.DEVNULL,
                             capture_output=True, text=True, timeout=60, check=False)
    require(version.returncode == 0 and version.stdout.strip() == VERSION_NEW, 'live worker dependency version')
    trace = subprocess.run(['/home/loucmane/gascity/bin/gc', '--city', str(CITY), 'trace', 'show', '--type',
                            'cycle_result', '--since', '2m', '--json'], env=ENV, cwd='/',
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=False)
    require(trace.returncode == 0, 'trace read refused')
    latest = latest_cycle(json.loads(trace.stdout)['records'], host['host']['pid'])
    draft = derive(receipt, latest['config_revision'])
    require(o.host_observation() == host and m5_acceptance() == m5, 'host or M5 pair changed during observation')
    ROOT.mkdir(mode=0o700)
    require(write('receipt.before.json', receipt_raw) == RECEIPT_OLD_SHA, 'receipt copy')
    draft_sha = write('receipt.input.draft.json', serialize(draft))
    revision_sha = write('revision.json', latest)
    result = dict(ok=True, draft_sha256=draft_sha, revision_sha256=revision_sha,
                  permission_revision=latest['config_revision'], worker_version=version.stdout.strip(),
                  receipt_before_sha256=RECEIPT_OLD_SHA, m5=m5, host=host, receipt_installed=False,
                  worker_launched=False)
    print(json.dumps(dict(result_sha256=write('result.json', result), draft_sha256=draft_sha,
                          permission_revision=latest['config_revision'])))


if __name__ == '__main__':
    main()
