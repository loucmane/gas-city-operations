"""Fresh ga-xyqo PREP: compose an UNINSTALLED one-worker image.

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
ROOT = Path('/var/tmp/ga-xyqo-prep-20260929-r1')
OLD_WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-xyqo'
PROMPT = HERE/'PRECLAIM.md'
BRIEF_SHA = '262f11178a05b5c927dd8d0d03d1627ad8c9e88e73fd36e2d037c43225023eac'
SCOPE_SHA = '020ec6bceaf5b6052ce3d5cb3fef30b07f9d9553c02fe4a2d144d06e963e8851'
PROMPT_SHA = 'ce3392169c5c9179a39c8a186d235e42e92ff951abdfba0147c357d8cbe7ce10'
HELPER_SHA = '833b4289c03b788f8e836c09ae73b2674e816d873fe4ba0587a2584b9af0d6b1'
PROBE_SHA = '76e3ea1543e0bfb53c658b5d1d6dd9d205f6c73347f743bc9f0c890d5428560f'
PERMISSIONS_SHA = '2074e4bf524d6c0e0e182970ac8c197f9734fc726e17029010121672610c0ccd'
WORKTREE = Path('/var/tmp/ga-xyqo-worktree-20260929-r1/result.json')
WORKTREE_SHA = '7258fd9a9c4b781fd26e770d0294d8bc89279d28a7f7d5ce21c013028d17c58c'
TERMINAL = Path('/var/tmp/ga-rq5n-terminal-20260929-r2/result.json')
TERMINAL_SHA = 'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'
CLOSE = Path('/var/tmp/ga-rq5n-r2-close-20260929T173617Z/result.json')
CLOSE_SHA = 'd0cdd9206d87d6b646f945a9b4a0dea9fc6a81a23db60770698f1d4748e6e7c3'


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
    assert w['worktree'] == WORK and w['branch'] == 'codex/ga-xyqo-c1-package'
    assert w['base'] == '801a5a9d5b0d72f665c949a86573357f02c9f1ac'
    assert all(w.get(k) is True for k in ('ok', 'tracked_clean', 'default_rules_unchanged'))
    assert w['worker_launched'] is False and w['execution_authorized_by_this_result'] is False
    t = json.loads(old.read(TERMINAL, TERMINAL_SHA))
    assert all(t.get(k) is True for k in ('ok', 'actual_host_verified',
        'terminal_suspension_endpoint_bound', 'accepted_restoration_bound'))
    c = json.loads(old.read(CLOSE, CLOSE_SHA))
    assert c == dict(ok=True, closed_session='ci-b93t8', open_sessions=0,
        city_tmux_sessions=0, worktree_processes=0, tmux_server_killed=False,
        signals_sent=False,
        executor_sha256='c60138f899b2cfed940a59c6074a3ed7e200fa195a4a48a37bc700e14e482617')


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
            data = dict(data, task='ga-xyqo', worktree=WORK, prompt_path=str(PROMPT),
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
