"""Fresh ga-rq5n PREP: compose an UNINSTALLED one-worker image.

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
ROOT = Path('/var/tmp/ga-rq5n-prep-20260929-r1')
OLD_WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-rq5n'
PROMPT = HERE/'PRECLAIM.md'
BRIEF_SHA = '9a67e4c3ca3dad0e9a7b487ff1b911c3e10bf87df543d935a10327c5f7a6a247'
SCOPE_SHA = 'cd7afa08120db1ae10dca98d0dbd52c4dd10c7b8473cd4de4d6817ac16134e51'
PROMPT_SHA = 'bb085c55cf5639a790c62a5f40184fd347573ba6c174de7dbff1d3c1034532f3'
HELPER_SHA = '007634a77211aa26b2f801e5a47b0daeae2ccf132507cf36a7d754723c7af79a'
PROBE_SHA = 'eb56cfc38350e2ca2cfd614d5fb30b460716b58239558ca8d747ec692024b97a'
PERMISSIONS_SHA = '470b0afc0cca1c55005f716676949e2a96f0dddd912be94fa5f3fd046bf1dc76'
WORKTREE = Path('/var/tmp/ga-rq5n-worktree-20260929-r1/result.json')
WORKTREE_SHA = '163cfd690bcd1f0ca7586d3f1f8bad12f49a8a2a7fb5bb8d48175c5b0acf354c'
TERMINAL = Path('/var/tmp/ga-9olv-terminal-20260929-r1/result.json')
TERMINAL_SHA = 'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'
CLOSE = Path('/var/tmp/ga-9olv-r1-close-20260929T150920Z/result.json')
CLOSE_SHA = '39aa02a765eb0790dff9aff5f0aac7ab4658733e624b2186a89c623636d62e13'


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
    assert w['worktree'] == WORK and w['branch'] == 'codex/ga-rq5n-c1-package'
    assert w['base'] == '801a5a9d5b0d72f665c949a86573357f02c9f1ac'
    assert all(w.get(k) is True for k in ('ok', 'tracked_clean', 'default_rules_unchanged'))
    assert w['worker_launched'] is False and w['execution_authorized_by_this_result'] is False
    t = json.loads(old.read(TERMINAL, TERMINAL_SHA))
    assert all(t.get(k) is True for k in ('ok', 'actual_host_verified',
        'terminal_suspension_endpoint_bound', 'accepted_restoration_bound'))
    c = json.loads(old.read(CLOSE, CLOSE_SHA))
    assert c == dict(ok=True, closed_session='ci-0xi2z', open_sessions=0,
        city_tmux_sessions=0, worktree_processes=0, tmux_server_killed=False,
        signals_sent=False,
        executor_sha256='73c6528a0d486d664d8bfc23bbf06cf0f3ec346713f57da6c7306a17ddfeb1b3')


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
            data = dict(data, task='ga-rq5n', worktree=WORK, prompt_path=str(PROMPT),
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
