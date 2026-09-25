"""Seventh successor s1 (ga-e0t1.15 S4): derive the ga-qcwl window package from the reviewed ga-nibd package.

  python3 -B make_successor.py <output package dir>

S4 is the no-KICK acceptance window for the ga-e0t1.15 deployment (PLAN.md S4). After S2 (Core gc b2760ea4,
build source 9faeabc2, with the ga-odny nudge-on-route payload fix and the ga-nibd typed routing cycles),
S3 part 1 (M6 metadata, manifest file 7f335ad8) and S3 part 2 (P7, worker receipt 7cf59ab9 at revision
2113693e, Template cfd353f3 with the gct-jkgf role-prompt fix), one worker must claim its routed task from
Core's own nudge, with its role prompt first, and no coordinator KICK.

1. Every source is read from the ga-nibd s2 r2 commit object (ebbba629), never from a working tree.
2. Dropped: README.md, the tests and the generator (this package's own replace them); KICK (kick-r1.py and
   operator/KICK-1..3.sh, since S4 forbids it); RECONCILE (reconcile-predecessor-r3.py and
   operator/RECONCILE.sh): ga-nibd closed delivered, and a read-only check on 2026-09-25 found no Bead routed
   to or assigned to gascity/gc.implementation-worker in the rig or the city, so no predecessor must be held.
3. Identity: ga-nibd becomes ga-qcwl in paths, roots, worktree (ga-qcwl-provider-pins), branch, staging
   path, evidence path, probe test and Bead id. History comments that describe ga-nibd events stay (KEEP).
4. Host epoch after S2: the supervisor is PID 2940569 (start 123479699122) and the controller traces with
   that PID; the broker is active (2940285, start 123477220085); the signer and boot are unchanged. The Core
   image is gc b2760ea4, so the reused P6 support observer is rebound to it after load.
5. Accepted image: the P7 adoption's after.json (7e008d9b) and its provider pins (82a4a70c), taken on this
   epoch after S2 and S3 and read back twice (LIVE_PASS). The layered P6-era dispositions (historical cache
   times, epoch, ga-4z38 restore, coordinator cache, ga-gegx recovery) no longer apply and are not called.
6. Receipt staging: the P7 witness (afe4969d), the P7 input draft (c047b4d9), receipt 7cf59ab9 and revision
   2113693e are the baseline side. The isolated side is re-pinned by s2 from a fresh PREP run.
7. PREP rebinds to the diagnostics rebuilt at Core 9faeabc2 (compose e123ee37, preflight 510f4d72), because the
   new core pack changes the composed revision; the overlay is the ga-nibd PREP r6 overlay with only the work
   dir and header replaced.
8. Integrity: the platform inspector rebuilt at Core 9faeabc2 with the M6 manifest pin (334cc3c9, build record
   145a4841, entrypoint 585e0d37); the observers pin the M6 manifest file 7f335ad8.
9. The worker base is Core main b6843d3f (tree c9f19d21, equal to the running build source), and the source
   release admits exactly the ga-qcwl files. The brief's task sections are replaced for ga-qcwl.
10. Digest propagation to a fixed point.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

SOURCE = 'ebbba629c2430418ca60d05f206a4e821538ad2c'
WORKTREE = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-nibd-window/'
HERE = Path(__file__).resolve().parent
DROP = {'README.md', 'test_successor.py', 'kick-r1.py', 'operator/KICK-1.sh', 'operator/KICK-2.sh',
        'operator/KICK-3.sh', 'reconcile-predecessor-r3.py', 'operator/RECONCILE.sh'}
DROP_DIRS = ('generators/',)
DIGEST = re.compile(r'[0-9a-f]{64}')

KEEP = ['r6 (ga-nibd): the ga-gegx prep, rebound to the ga-nibd worktree and header; nothing else',
        '# ga-nibd: after a worker session ran', '# ga-nibd disposition, for independent review']

IDENTITY = [
    ('/home/loucmane/gascity-core-worktrees/ga-nibd-typed-route-cycles',
     '/home/loucmane/gascity-core-worktrees/ga-qcwl-provider-pins'),
    ('codex/ga-nibd-typed-route-cycles', 'codex/ga-qcwl-provider-pins'),
    ('/designs/ga-nibd-window', '/designs/ga-qcwl-window'),
    ('gas-city-staging/ga-nibd-window', 'gas-city-staging/ga-qcwl-window'),
    ('/var/tmp/ga-nibd-', '/var/tmp/ga-qcwl-'),
    ('ga-nibd', 'ga-qcwl'),
    ('TestGanibdCapabilityProbeNoTests', 'TestGaqcwlCapabilityProbeNoTests'),
]

GC_OLD, GC_NEW = ('69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9',
                  'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489')
BASE_OLD, BASE_NEW = 'e6366b9ececd3a4ceab2bcaa264a5e317e6eab88', 'b6843d3f539eeebaf9d9c12e7d095d25cdee585d'
TREE_OLD, TREE_NEW = 'f2c120a5ac9ea25ebc395c1b3cfa4eb30dcafd13', 'c9f19d215d271a5dda0bce296dc72c32dfc35499'
CORE_OLD, CORE_NEW = '796d9a7a67c42294fdc467c107bb59b76e482301', '9faeabc2892d8c7133111e13ad55af66790a2ac6'
M5_FILE, M6_FILE = ('2d7eadce62c4e567697813cc9122414f1e94c3bd9d389aef92015adef7f36319',
                    '7f335ad83091a1a907b628fa5813c7daf6a530340a2ed404476797b5db90fefb')
RECEIPT_OLD, RECEIPT_NEW = ('0b30c23f4484382fd4918f394599268f4f4005ac71118e8a7f82ca72eb9615ff',
                            '7cf59ab9e5a43fd7bca97028e7faaa2b2f9bfb927a663b4588c66e846e4e425d')
REVISION_OLD, REVISION_NEW = ('d6ca85cd96c7aab4ea0b6a7954d2d74e5e6bb211cde0bb820f3b6f815023bd88',
                              '2113693eefd3a9c905554a294e36ab3b5a17bc63004280b7144ff069ef75acc2')
INSPECTOR = ('/var/tmp/ga-e0t1.15-platform-inspector-20260925',
             '334cc3c912858d84582cf980cf7f270ebb6e5250ac3a62dbdf4e720dc0a2564f',
             '145a48417718adf62cf607e74424147884b6247f44ff7f33dfa8971767ec1dc4',
             '585e0d376d90a26cab57d6e676d4aa3567df53b4c8b10816e8fac8071901a7f7')
PREP_OVERLAY = Path('/var/tmp/ga-nibd-prep-20260925-r1/city.isolated.toml')
PREP_OVERLAY_SHA = 'c38c6cb43b6c1124529d66e1a10e1d69fc8cb3b21d4f1f12255de16dd991f5e9'
ALLOWED = ('internal/managedworker/preflight.go', 'internal/managedworker/preflight_test.go',
           'internal/api/handler_provider_readiness.go', 'internal/api/handler_provider_readiness_test.go',
           'internal/platforminstall/integrity.go', 'internal/platforminstall/integrity_test.go',
           'cmd/gc/managed_product_dispatch_gate.go', 'cmd/gc/managed_product_dispatch_gate_test.go',
           'cmd/gc/cmd_platform_canary.go', 'cmd/gc/cmd_platform_canary_test.go', '.gitignore')
# s2 fills these with the ga-qcwl PREP outputs (overlay, receipt image, revision, result); s1 keeps ga-nibd's.
PREP_PINS = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.run(['git', '--no-optional-locks', '-C', WORKTREE, *args], check=True,
                          capture_output=True).stdout


def sources():
    names = git('ls-tree', '-r', '--name-only', SOURCE, PREFIX).decode().split('\n')
    files = {}
    for path in names:
        if not path:
            continue
        name = path[len(PREFIX):]
        if name in DROP or name.startswith(DROP_DIRS):
            continue
        files[name] = git('show', SOURCE + ':' + path)
    return files


def successor_overlay():
    raw = PREP_OVERLAY.read_bytes()
    assert sha(raw) == PREP_OVERLAY_SHA
    text = raw.decode()
    for old, new in (('ga-nibd-typed-route-cycles', 'ga-qcwl-provider-pins'),
                     ('# ga-nibd bounded one-worker window', '# ga-qcwl bounded one-worker window')):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text.encode()


def sub(text, old, new, count=1):
    assert text.count(old) == count, (old[:70], text.count(old))
    return text.replace(old, new)


def rename(text):
    for index, phrase in enumerate(KEEP):
        text = text.replace(phrase, '\x00KEEP%d\x00' % index)
    for old, new in IDENTITY:
        text = text.replace(old, new)
    for index, phrase in enumerate(KEEP):
        text = text.replace('\x00KEEP%d\x00' % index, phrase)
    return text


def window_base(text):
    text = sub(text, "BASE = '%s'" % BASE_OLD, "BASE = '%s'" % BASE_NEW)
    text = sub(text, "WITNESS = Path('/var/tmp/gct-m1wh-p6-adoption-20260923-r2/typed-support.json')\n"
                     "WITNESS_SHA = '5a630443b7b47c0054b96f593b18d3012ac671d4124c25eae3afa54bcfe8cfeb'\n",
               "WITNESS = Path('/var/tmp/ga-e0t1.15-p7-adoption-20260925/typed-support.json')\n"
               "WITNESS_SHA = 'afe4969df9076ffe139af41ba4626ed374a3c0e4c224efd9762e02036066a71f'\n")
    text = sub(text, "RECEIPT_SHA = ('%s'," % RECEIPT_OLD, "RECEIPT_SHA = ('%s'," % RECEIPT_NEW)
    text = sub(text, "REVISION = ('%s'," % REVISION_OLD, "REVISION = ('%s'," % REVISION_NEW)
    text = sub(text, "INPUT = (Path('/var/tmp/gct-m1wh-p6-input-20260923-r2/receipt.input.draft.json'), PREP/'receipt.input.json')\n"
                     "INPUT_SHA = ('24c1ca751303d5cab12a1605599d13cb5e5a152c977088fbb6869c7a052095ec',\n",
               "INPUT = (Path('/var/tmp/ga-e0t1.15-p7-input-20260925/receipt.input.draft.json'), PREP/'receipt.input.json')\n"
               "INPUT_SHA = ('c047b4d909095406d359808fecca6a417905435d6c4a3c9a270d5d0b941cd9bb',\n")
    text = sub(text, "ACCEPTED = Path('/var/tmp/gct-m1wh-p6-adoption-20260923-r2/after.json')\n"
                     "ACCEPTED_SHA = '1c025ef9ef31d75f7becb6e6ed1fd426f3d318eb53913cf8e24888f163900b70'\n"
                     "PROVIDER_SHA = 'a5f7f8c11a95b48d01f910c5c4668828d61a587a5942545f27d403ebadfeac8f'\n",
               "# S4: the accepted image is the P7 adoption snapshot on the post-S2/S3 host (two LIVE_PASS readbacks).\n"
               "ACCEPTED = Path('/var/tmp/ga-e0t1.15-p7-adoption-20260925/after.json')\n"
               "ACCEPTED_SHA = '7e008d9be0abd067270cf43fc1236cab7fab543a7339486f05422bb62002c56d'\n"
               "PROVIDER_SHA = '82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b'\n")
    text = sub(text, "    o = b.observe_module()\n    o.ENV = dict(o.ENV, BD_DISABLE_METRICS='1')\n",
               "    o = b.observe_module()\n"
               "    # S4: the reused P6 observer pins the pre-S2 image; rebind it to the running Core (b_gc_sha).\n"
               "    o.GC_SHA = b_gc_sha()\n"
               "    o.ENV = dict(o.ENV, BD_DISABLE_METRICS='1')\n")
    text = sub(text, "    for name, pid, start in [('core','2331','39708112'), ('signer','2310','39660502'), ('broker','0','0')]:\n",
               "    # S4: the S2 supervisor epoch; the broker has stayed active since the sequence 14 install.\n"
               "    for name, pid, start in [('core','2940569','123479699122'), ('signer','2310','39660502'),\n"
               "                             ('broker','2940285','123477220085')]:\n")
    text = sub(text, "    return '%s'\n" % GC_OLD, "    return '%s'\n" % GC_NEW)
    text = sub(text, "value['controller']['pid']==2331,", "value['controller']['pid']==2940569,")
    text = sub(text, "require(newest['controller_pid']==2331, 'controller trace epoch drift')",
               "require(newest['controller_pid']==2940569, 'controller trace epoch drift')")
    text = sub(text, "        image = approved_coordinator_cache_image(approved_restore_image(approved_epoch_image(approved_historical_image(prior), h)))\n"
                     "        if RECOVERY is not None:\n"
                     "            image = approved_recovery_image(image, *RECOVERY)\n",
               "        # S4: the P7 snapshot was taken on this epoch after S2 and S3; no P6-era disposition applies.\n"
               "        require(RECOVERY is None, 'no recovery admission in S4')\n"
               "        image = prior\n")
    text = sub(text, "ga-qcwl r11: a rebind of the reviewed ga-y49e base window-state-r6-read-safe.py (b10a3810) onto the\n"
                     "M5 baseline and task ga-qcwl.",
               "ga-qcwl r11: a rebind of the reviewed ga-y49e base window-state-r6-read-safe.py (b10a3810) onto the\n"
               "post-S3 baseline (M6 metadata, receipt 7cf59ab9, gc b2760ea4) and task ga-qcwl.")
    for old, new in PREP_PINS:
        text = sub(text, "'%s'" % old, "'%s'" % new)
    return text


def prep(text):
    for old, new in (
            ("GC_SHA = '%s'" % GC_OLD, "GC_SHA = '%s'" % GC_NEW),
            ("COMPOSE = Path('/var/tmp/ga-ecwh-compose-diagnostic-20260920-r2/compose')\n"
             "COMPOSE_SHA = '9f837c831919cd440089ac2207c6e32ca005709b51a72e430a48f76006f2edd3'\n",
             "COMPOSE = Path('/var/tmp/ga-e0t1.15-compose-diagnostic-20260925/compose')\n"
             "COMPOSE_SHA = 'e123ee37c020b3c1aae703f2956f7b59a322fd4814cea7fe2e5a96dc6c920a76'\n"),
            ("BUILD = Path('/var/tmp/ga-ecwh-preflight-diagnostic-20260920-r1')\n"
             "FINALIZE_SHA = 'edbc0fa11d3ebae15f678179725203d9da3434ec0cf8883c536398d5f97426bf'\n",
             "BUILD = Path('/var/tmp/ga-e0t1.15-preflight-diagnostic-20260925')\n"
             "FINALIZE_SHA = '510f4d728472e9500beabab0515a1a4e87d30a7c168c7f723f0c53a28f908619'\n"),
            ("PRIOR = Path('/var/tmp/gct-m1wh-p6-input-20260923-r2/receipt.input.draft.json')\n"
             "PRIOR_SHA = '24c1ca751303d5cab12a1605599d13cb5e5a152c977088fbb6869c7a052095ec'\n",
             "PRIOR = Path('/var/tmp/ga-e0t1.15-p7-input-20260925/receipt.input.draft.json')\n"
             "PRIOR_SHA = 'c047b4d909095406d359808fecca6a417905435d6c4a3c9a270d5d0b941cd9bb'\n"),
            ("RECEIPT_SHA = '%s'" % RECEIPT_OLD, "RECEIPT_SHA = '%s'" % RECEIPT_NEW),
            ("REVISION = '%s'" % REVISION_OLD, "REVISION = '%s'" % REVISION_NEW)):
        text = sub(text, old, new)
    overlay = sha(successor_overlay())
    text = sub(text, "OVERLAY_SHA = '%s'" % PREP_OVERLAY_SHA, "OVERLAY_SHA = '%s'" % overlay)
    text = sub(text, "'overlay bytes differ from the derived %s'" % PREP_OVERLAY_SHA[:8],
               "'overlay bytes differ from the derived %s'" % overlay[:8])
    text = sub(text, "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n",
               "\nr7 (ga-qcwl, ga-e0t1.15 S4): the ga-nibd prep on the post-S3 host: gc b2760ea4, receipt 7cf59ab9,\n"
               "revision 2113693e, the P7 input draft, and the compose and preflight diagnostics rebuilt at Core\n"
               "9faeabc2 (the new core pack changes the composed revision). The overlay is the ga-nibd r6 overlay with\n"
               "only the work dir and header lines replaced.\n"
               "\nWhat it does, all in read-only, network-isolated bwrap namespaces:\n")
    return text


def observer(text, name):
    root, binary, record, entry = INSPECTOR
    text = sub(text, "BUILD=Path('/var/tmp/ga-4z38-platform-inspector-20260924-r1')", "BUILD=Path('%s')" % root)
    text = sub(text, "BINARY_SHA='b8ebcde38a9ee8078752949226f6736ea14a25413fba73db4d95076261658d13'", "BINARY_SHA='%s'" % binary)
    text = sub(text, "MANIFEST_SHA='%s'" % M5_FILE, "MANIFEST_SHA='%s'" % M6_FILE)
    text = sub(text, "'39bfcea56f8932623d6b60ffe745de9f7029e76ba01fdd0d7da90c2fc402eaf9'", "'%s'" % record)
    text = sub(text, "result['core_commit']=='%s'" % CORE_OLD, "result['core_commit']=='%s'" % CORE_NEW)
    text = sub(text, "result['core_tree']=='%s'" % TREE_OLD, "result['core_tree']=='%s'" % TREE_NEW)
    text = sub(text, "result['entrypoint_sha256']=='e5e9872f2b57d70c9fbde8e3d152978eaf9266453af67dbd1a82a4d1886b7ca3'",
               "result['entrypoint_sha256']=='%s'" % entry)
    if name == 'observe-integrity-r11.py':
        text = sub(text, "RECOVER_ROOT='/var/tmp/ga-gegx-recover-20260925-r3'\n"
                         "RECOVER_SHA='b6ad8162b8eec1a26a07b63a3e6f0238e1dad116533b31ed0e7cf494b641c02e'\n", '')
        text = sub(text, "    # s6: admit the city.toml the recovery job restored (window-base approved_recovery_image).\n"
                         "    w.RECOVERY=(RECOVER_ROOT,RECOVER_SHA)\n",
                   "    # S4: no recovery admission; the accepted image is the P7 snapshot (window-base).\n")
        text = sub(text, "M5 baseline. It admits the live state against the P6 accepted snapshot plus the reviewed dispositions,\n",
                   "post-S3 baseline (M6). It admits the live state against the P7 adoption snapshot (ga-e0t1.15 S4),\n")
        text = sub(text, "    # Fresh window: no prior lifecycle chain exists to verify. The suspension state is pinned in the\n"
                         "    # snapshot below and admitted against the recorded TERMINAL entry (approved_restore_image).\n",
                   "    # Fresh window: no prior lifecycle chain exists to verify. The suspension state is pinned in the\n"
                   "    # snapshot below and compared exactly with the P7 adoption snapshot.\n")
        text = sub(text, "    # The base snapshot named before.json admits the live state against the P6 accepted snapshot\n"
                         "    # with the reviewed dispositions approved_historical_image, approved_epoch_image,\n"
                         "    # approved_restore_image, approved_coordinator_cache_image and (with RECOVERY set above)\n"
                         "    # approved_recovery_image, and the accepted provider pins.\n",
                   "    # The base snapshot named before.json admits the live state against the P7 adoption snapshot\n"
                   "    # (two LIVE_PASS readbacks) and its provider pins; no P6-era disposition applies.\n")
    text = sub(text, 'admitted_against_p6_with_disposition=True', 'admitted_against_p7_snapshot=True',
               1 if name == 'observe-integrity-r11.py' else 0)
    return text


def release(text):
    text = sub(text, "BASE_COMMIT = '%s'" % BASE_OLD, "BASE_COMMIT = '%s'" % BASE_NEW)
    text = sub(text, "ALLOWED = {'internal/sling/cycle.go', 'internal/sling/cycle_test.go', "
                     "'internal/sling/sling_core_test.go', '.gitignore'}",
               'ALLOWED = {' + ', '.join("'%s'" % p for p in ALLOWED) + '}')
    return text


BRIEF_TASK = '''## Worker-owned implementation and tests

Core platform provider pins are keyed by provider name only, so two closed Claude wrappers cannot share one
receipt (Bead ga-qcwl; read its description with `bd show ga-qcwl --json`). Launch preflight probes provider
readiness by `provider.name`, readiness accepts only built-in names, the platform manifest refuses duplicate
provider names, and the whole-environment check compares every receipt profile's provider with the manifest pin
of the same name. Make several pinned wrappers of one provider family coexist: for example key the pins by name
and path (or a pin id the profile carries), or probe readiness by provider family rather than by pin name. Keep
every existing single-wrapper behaviour, every refusal of an unpinned, drifted or ambiguous provider, and the
fail-closed reads. No live change, no Template or Operations change, no receipt or manifest edit on disk.

Focused RED first, then GREEN:
- A receipt with the Core signing profile and two candidate claude-family profiles, each with its own wrapper
  path and digest, passes the dispatch gate's whole-environment comparison and the canary's profile scope.
- A duplicate identical pin, a wrapper whose bytes drift, an unpinned wrapper, and a profile naming a pin that
  does not exist are still refused.
- Readiness still accepts only built-in provider families.
- The existing single-profile tests stay green unchanged.

Run the complete `go test ./internal/managedworker ./internal/api ./internal/platforminstall`, the focused
`go test ./cmd/gc -run 'ManagedProduct|PlatformCanary|DispatchGate'`, the corresponding `go vet` of those
packages and `git diff --check`. Preserve RED and failed attempts. No unrelated broad suites or network fallback.
Capture checkpoint with exact identity, base, patch digest, changed paths, tests and limitations. Read back this
Bead before handoff. Do not modify parent plans or other Beads.
'''


def brief(text):
    text = sub(text, '# ga-qcwl — one actual Claude Core implementation/signing worker',
               '# ga-qcwl — one actual Claude Core implementation/signing worker (ga-e0t1.15 S4, no KICK)')
    text = sub(text, '- Initial HEAD %s.\n- Initial tree %s.\n' % (BASE_OLD, TREE_OLD),
               '- Initial HEAD %s.\n- Initial tree %s.\n' % (BASE_NEW, TREE_NEW))
    text = sub(text, '- Allowed source: internal/sling/cycle.go, internal/sling/cycle_test.go,\n'
                     '  internal/sling/sling_core_test.go and the exact .gitignore addition named in\n'
                     '  the source release.\n',
               '- Allowed source: ' + ', '.join(ALLOWED[:-1]) + ' and the exact .gitignore addition named in\n'
               '  the source release. Stage only those you actually change.\n')
    text = sub(text, "`go test ./internal/sling -run '^TestGaqcwlCapabilityProbeNoTests$'`",
               "`go test ./internal/managedworker -run '^TestGaqcwlCapabilityProbeNoTests$'`")
    text, found = re.subn(r'## Worker-owned implementation and tests\n.*?(?=\n## Artifact and managed signing contract\n)',
                          BRIEF_TASK.rstrip('\n'), text, flags=re.S)
    assert found == 1
    text = sub(text, 'After all tests, stage ONLY the three allowed source paths and .gitignore, with no',
               'After all tests, stage ONLY the allowed source paths you changed and .gitignore, with no')
    text = sub(text, "--message 'fix: distinguish routing dependency and hierarchy cycles'",
               "--message 'fix: let pinned wrappers of one provider family share a receipt'")
    return text


def rebind(files):
    out = {}
    for name, raw in files.items():
        text = raw.decode()
        text = rename(text)
        if name == 'window-base-r11.py':
            text = window_base(text)
        elif name == 'window-r11.py':
            text = sub(text, "w.require(newest['controller_pid']==2331 and 0<=age<=120,'stale/active controller revision')",
                       "w.require(newest['controller_pid']==2940569 and 0<=age<=120,'stale/active controller revision')")
            text = sub(text, "INSPECTOR_SHA='b8ebcde38a9ee8078752949226f6736ea14a25413fba73db4d95076261658d13'",
                       "INSPECTOR_SHA='%s'" % INSPECTOR[1])
            text = sub(text, 'admitted_against_p6_with_disposition=True,', 'admitted_against_p7_snapshot=True,')
        elif name == 'route-chain-r1.py':
            text = sub(text, "cycle['controller_pid']==2331", "cycle['controller_pid']==2940569")
        elif name == 'prep-r11.py':
            text = prep(text)
        elif name in ('observe-integrity-r11.py', 'observe-terminal-r11.py'):
            text = observer(text, name)
        elif name == 'release-r11.py':
            text = release(text)
        elif name == 'worker-brief.md':
            text = brief(text)
        elif name == 'operator/PREP.sh':
            text = sub(text, '# ga-qcwl window prep r6:', '# ga-qcwl window prep r7:')
            text = sub(text, '# staging log below. It is the reviewed ga-gegx prep, rebound to ga-qcwl, with\n',
                       '# staging log below. It is the reviewed ga-nibd prep (the ga-gegx prep) on the post-S3 host,\n'
                       '# rebound to ga-qcwl, with\n')
        out[name] = text.encode()
    # BIND runs for ga-qcwl, so ROUTE binds the new bind-task digest.
    route = out['route-task-r5.py'].decode()
    [ran] = re.findall(r"^BIND_SHA='([0-9a-f]{64})'$", route, re.M)
    out['route-task-r5.py'] = route.replace("BIND_SHA='%s'" % ran, "BIND_SHA='%s'" % sha(out['bind-task-r3.py'])).encode()
    keep = {'window-base-r11.py': set()}
    history = {name: {sha(raw)} for name, raw in files.items()}
    while True:
        for name, raw in out.items():
            history.setdefault(name, set()).add(sha(raw))
        renamed = {old: sha(out[n]) for n in out for old in history[n] if old != sha(out[n])}
        changed = False
        for name, raw in out.items():
            if not name.endswith(('.py', '.sh')):
                continue
            text = raw.decode()
            kept = keep.get(name, set())
            new = DIGEST.sub(lambda m: m.group(0) if m.group(0) in kept else renamed.get(m.group(0), m.group(0)), text)
            if new != text:
                out[name] = new.encode()
                changed = True
        if not changed:
            break
    return out


def main(output):
    out = rebind(sources())
    root = Path(output)
    for name, data in sorted(out.items()):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if name.endswith('.sh') and (root/name).stat().st_mode & 0o111 else 0o644)
    print(len(out), 'files written to', root)


if __name__ == '__main__':
    main(*sys.argv[1:])
