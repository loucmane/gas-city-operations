"""Fresh ga-9olv PREP: compose an UNINSTALLED one-worker image.

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
ROOT = Path('/var/tmp/ga-9olv-prep-20260929-r1')
OLD_WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-9olv'
PROMPT = HERE/'PRECLAIM.md'
BRIEF_SHA = '9106ebe3b931946af94f40990a7e681e97f23f9662d0f8074c2506219230cd7a'
SCOPE_SHA = '7e8ae5d859b62751b5f4eb0e752d28f545167585b479bb3b62ab835d1a76b2c5'
PROMPT_SHA = '7781bc962112b57fadc034606385c1dd2ec04a1380b580b5d83f84b4416f41dc'
HELPER_SHA = 'f5fcd2956f637025d6424f45c6fe66aa636beacf0285d0466f10491df9adafc9'
PROBE_SHA = 'd52e98dd6ef8b9450b5523e7ccf034e03bf2e19d8af47e1e284a10e8d0cf8c25'
PERMISSIONS_SHA = '4428d83183beb88fb1b321b124fb1514c11f7e861afb6cf5c24242e7990e5371'
WORKTREE = Path('/var/tmp/ga-9olv-worktree-20260929-r1/result.json')
WORKTREE_SHA = '3d68c8d1ed1b4a929dd908af40245a49e9f7ddc3ec93cae2275a4c5e5e115a8f'
TERMINAL = Path('/var/tmp/ga-x2wz-terminal-20260929-r1/result.json')
TERMINAL_SHA = 'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'
CLOSE = Path('/var/tmp/ga-x2wz-r1-close-20260929T121217Z/result.json')
CLOSE_SHA = '86b0717286af9d953f0ced2abfee8070e5f91b44fe0123d9d95d4dc8dc5afc3e'


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
    assert w['worktree'] == WORK and w['branch'] == 'codex/ga-9olv-c1-package'
    assert w['base'] == '801a5a9d5b0d72f665c949a86573357f02c9f1ac'
    assert all(w.get(k) is True for k in ('ok', 'tracked_clean', 'default_rules_unchanged'))
    assert w['worker_launched'] is False and w['execution_authorized_by_this_result'] is False
    t = json.loads(old.read(TERMINAL, TERMINAL_SHA))
    assert all(t.get(k) is True for k in ('ok', 'actual_host_verified',
        'terminal_suspension_endpoint_bound', 'accepted_restoration_bound'))
    c = json.loads(old.read(CLOSE, CLOSE_SHA))
    assert c == dict(ok=True, closed_session='ci-di744', open_sessions=0,
        city_tmux_sessions=0, worktree_processes=0, tmux_server_killed=False,
        signals_sent=False,
        executor_sha256='55cfc116a74de8e7a79447514aab578c11fc9e74481923ddf90500bd15f219fa')


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
            data = dict(data, task='ga-9olv', worktree=WORK, prompt_path=str(PROMPT),
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
