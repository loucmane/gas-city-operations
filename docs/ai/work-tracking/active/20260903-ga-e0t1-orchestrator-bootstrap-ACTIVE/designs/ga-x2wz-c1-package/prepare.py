"""Fresh ga-x2wz PREP: compose an UNINSTALLED one-worker image.

Reuse the pinned S1/S5 preparation and R11 prompt/runtime proof. Retarget only
the candidate workspace and preclaim prompt. No BIND, route, resume, install or
worker launch is reachable. Historical operations and roots are never replayed.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import types

HERE = Path(__file__).parent
SEED = HERE.parent/'ga-e0t1.20-astra-bootstrap/prepare.py'
SEED_SHA = '40858f94e795425c38f1e5ae8b973aa60e5c3aa67043bc84b6be36389b4ea6c3'
ROOT = Path('/var/tmp/ga-x2wz-prep-20260929-r1')
OLD_WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-x2wz'
PROMPT = HERE/'PRECLAIM.md'
BRIEF_SHA = 'c389dc4a1a624c8cf0193e346fc1b8fb230a08dfee47d512915c717ff9c1b6b8'
SCOPE_SHA = '3ffdeb52a9d527d3a598cde728ecea590baca02ef10b4c61bd5a952de697f31e'
PROMPT_SHA = '2b0bf9bae1983e7efd8015233d45c9e26db9cc1d360b7c271b97e498ec8f1d58'
HELPER_SHA = 'ba000888f2d5de3d88ae7c5026e16071ff40466a1775772a316b3efa42f10b42'
PROBE_SHA = 'b7c33d703ebc2ba30df2074ea392abcdb94b7c596cc4b27d3ab42d2bf8e80c3c'
PERMISSIONS_SHA = '29b9e38fc676fa1e21a1ef94aa4b310f43bae5f0e268915eeba42a762aad3e15'
WORKTREE = Path('/var/tmp/ga-x2wz-worktree-20260929-r1/result.json')
WORKTREE_SHA = 'a538ebb3a89a6f5f4c6dfda34ee86898c5aa58f7e33bead51e4dd06ec3546caf'
TERMINAL = Path('/var/tmp/ga-1aa1-terminal-20260929-r1/result.json')
TERMINAL_SHA = 'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'
CLOSE = Path('/var/tmp/ga-1aa1-r1-close-20260929T092941Z/result.json')
CLOSE_SHA = '4f6022338f77c1d02e5fbbac78a513bb29f78aeebb52ff32a153ca8181624a57'


def retarget(frozen):
    counts = {'city.window-r2.toml': 3, 'city.window-r3.toml': 4,
        'window-r2-declared-delta.json': 3, 'config.baseline.json': 0,
        'orders.baseline.json': 0, 'window-restrictions.rules': 0}
    assert set(frozen) == set(counts), 'seed input inventory'
    result = {}
    for name, raw in frozen.items():
        assert raw.count(OLD_WORK.encode()) == counts[name], 'workspace occurrence drift: '+name
        assert WORK.encode() not in raw, 'seed already retargeted'
        result[name] = raw.replace(OLD_WORK.encode(), WORK.encode())
    return result


def prove_completed_inputs(old):
    w = json.loads(old.read(WORKTREE, WORKTREE_SHA))
    assert w['worktree'] == WORK and w['branch'] == 'codex/ga-x2wz-c1-package'
    assert w['base'] == 'bf369ae41cf512f5f5563f842cadff394457da4c'
    assert all(w.get(k) is True for k in ('ok', 'tracked_clean', 'default_rules_unchanged'))
    assert w['worker_launched'] is False and w['execution_authorized_by_this_result'] is False
    t = json.loads(old.read(TERMINAL, TERMINAL_SHA))
    assert all(t.get(k) is True for k in ('ok', 'actual_host_verified',
        'terminal_suspension_endpoint_bound', 'accepted_restoration_bound'))
    c = json.loads(old.read(CLOSE, CLOSE_SHA))
    assert c == dict(ok=True, closed_session='ci-08vl1', open_sessions=0,
        city_tmux_sessions=0, worktree_processes=0, tmux_server_killed=False,
        signals_sent=False,
        executor_sha256='b9c40e61f3f9df327e7e5d83f12a064740c48ed070c69be223cada4bb39df269')


def receipt_contract(before, final, observed):
    assert len(before['profiles']) == 3 and {p['name'] for p in before['profiles']} == {
        'gascity/gc.implementation-worker', 'gascity/operations-candidate-worker',
        'gas-city-template/gc.implementation-worker'}, 'typed profile inventory'
    assert final['profiles'] == before['profiles'], 'typed profiles changed'
    assert final['permission_revision'] == observed['permission_revision'], 'native revision drift'
    assert sorted(k for k in set(before) | set(final) if before.get(k) != final.get(k)) == [
        'permission_revision', 'receipt_sha256'], 'unexpected receipt delta'


def configure():
    raw = SEED.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SEED_SHA, 'preparation seed drift'
    seed = types.ModuleType('ga1_prep_seed')
    seed.__file__ = str(SEED)
    exec(compile(raw, str(SEED), 'exec', dont_inherit=True), seed.__dict__)
    original_inputs = seed.inputs
    seed.inputs = lambda old: retarget(original_inputs(old))
    seed.WORK = WORK
    assert seed.RESUME.count(OLD_WORK) == 1
    seed.RESUME = seed.RESUME.replace(OLD_WORK, WORK)
    inherited = seed.load()
    native_receipt_image = inherited.receipt_image
    old = seed.configure(inherited)
    old.ROOT = ROOT
    old.read(PROMPT, PROMPT_SHA)
    old.read(HERE/'WORKER-BRIEF.md', BRIEF_SHA)
    old.read(HERE/'FILE-SCOPE.json', SCOPE_SHA)
    helper = old.module(HERE/'launch-contract.py', HELPER_SHA, 'ga1_launch_contract')
    prove_completed_inputs(old)
    prior = HERE.parent/'ga-e0t1-20-astra-window'
    runtime = old.module(prior/'runtime-process-r7.py',
        'ea63f0ffda927baa34b777aeb210bf37cd7d7b408a629a9db9abc32445d40e65', 'ga1_runtime')
    probe = old.module(HERE/'worker-startup.py', PROBE_SHA, 'ga1_startup')
    permissions = old.module(HERE/'permissions-baseline.py', PERMISSIONS_SHA, 'ga1_permissions')

    def verify_host_assets():
        # Called only by the host branch, never from the namespace normalize child.
        runtime.verify_assets(probe.read_regular)
        permissions.verify(old.read, old.module)

    old._verify_host_assets = verify_host_assets
    original_build, original_expected = old.build_overlay, old.expected_config

    def build(city, baseline, orders):
        raw, patches, names, target, selected = original_build(city, baseline, orders)
        marker = b'[[patches.agent]]\ndir = "gascity"\nname = "codex"\nsuspended = false\n'
        assert raw.count(marker) == 1, 'target prompt patch not unique'
        changed = raw.replace(marker, marker+('prompt_template = '+json.dumps(str(PROMPT))+'\n').encode())
        old.OVERLAY_SHA = old.sha(changed)
        return changed, patches, names, target, selected

    def expected(*args):
        value = original_expected(*args)
        changed = copy.deepcopy(value)
        [target] = [a for a in changed['config']['Agents'] if (a['Dir'], a['Name']) == ('gascity', 'codex')]
        target['PromptTemplate'] = str(PROMPT)
        helper.config_delta(value, changed, str(PROMPT))
        return changed

    def image(*args):
        before = json.loads(old.read(old.RECEIPT, old.RECEIPT_SHA))
        wire = native_receipt_image(*args)
        receipt_contract(before, json.loads(wire), json.loads(old.read(ROOT/'composition.after.json')))
        return wire

    old.build_overlay, old.expected_config, old.receipt_image = build, expected, image
    original_write = old.write

    def write(name, data, root=None):
        if name == 'result.json':
            old._verify_host_assets()
            data = dict(data, task='ga-x2wz', worktree=WORK, prompt_path=str(PROMPT),
                worker_brief_sha256=BRIEF_SHA, file_scope_sha256=SCOPE_SHA,
                prompt_sha256=PROMPT_SHA, worker_probe_sha256=PROBE_SHA,
                completed_worktree_sha256=WORKTREE_SHA, prior_terminal_sha256=TERMINAL_SHA,
                prior_close_sha256=CLOSE_SHA, permission_capture_sha256=permissions.RESULT_SHA,
                preserved_transcript_sha256=permissions.TRANSCRIPT_SHA)
        return original_write(name, data, root)

    old.write = write
    old._SOURCE_SHA = globals().get('_SOURCE_SHA')
    return old


if __name__ == '__main__':
    old = configure()
    assert old._SOURCE_SHA and old.read(Path(__file__), old._SOURCE_SHA), 'source launcher required'
    if len(sys.argv) == 3 and sys.argv[1] == 'normalize':
        assert sys.argv[2] == str(ROOT), 'wrong normalize root'
        old.normalize_main(ROOT)
    else:
        assert len(sys.argv) == 1
        old._verify_host_assets()
        old.main()
