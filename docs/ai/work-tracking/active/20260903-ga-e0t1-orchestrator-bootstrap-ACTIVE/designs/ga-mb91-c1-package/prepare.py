"""Fresh ga-mb91 PREP: compose an UNINSTALLED one-worker image.

Reuse the pinned S1/S5 preparation and R11 prompt/runtime proof. Retarget only
the candidate workspace and preclaim prompt. No BIND, route, resume, install or
worker launch is reachable. Historical operations and roots are never replayed.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tomllib
import types

HERE = Path(__file__).parent
SEED = HERE.parent/'ga-e0t1.20-astra-bootstrap/prepare.py'
SEED_SHA = '40858f94e795425c38f1e5ae8b973aa60e5c3aa67043bc84b6be36389b4ea6c3'
ROOT = Path('/var/tmp/ga-mb91-prep-20260930-r1')
OLD_WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91'
PROMPT = HERE/'PRECLAIM.md'
BRIEF_SHA = '06668effcbad44da933cbe6168f29a734027ddf87b527ea3f19d9a316aa1872d'
SCOPE_SHA = '020ec6bceaf5b6052ce3d5cb3fef30b07f9d9553c02fe4a2d144d06e963e8851'
PROMPT_SHA = '09472ad7d608c6207c6ba8f79725603ff217c2cdaf48a7f0061b32e2e4d93944'
HELPER_SHA = '96560832152e6f653e305ddb2f95b5fcc43f73f6a22b05f01695dfb37016d489'
PROBE_SHA = '327d9928b4167642d67a1899f64dafca36ba460012a6ea7e03dfb04bbb86d0e1'
PERMISSIONS_SHA = 'c1c30b227a6e65dd900e9a54aae5e67821aa771b9a7e9285aff99aa4f22e47d9'
WORKTREE = Path('/var/tmp/ga-mb91-worktree-20260930-r1/result.json')
WORKTREE_SHA = 'c95506c64aca2b7765ce6e39982cfbc91448dbbc019c352b29520d1637297e9a'
TERMINAL = Path('/var/tmp/ga-jcxb-terminal-20260930-r1/result.json')
TERMINAL_SHA = 'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'
CLOSE = Path('/var/tmp/ga-jcxb-r1-close-20260930T041304Z/result.json')
CLOSE_SHA = '8f65d7d473dacdddbb6a6654f74c6d749346375bf47b3989f335ca229e3d656c'


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
    # Core PR50 adds precisely this default-valued field to config serialization.
    # Nothing else about the frozen effective baseline is relaxed or refreshed.
    baseline = json.loads(result['config.baseline.json'])
    assert 'NudgeQueueScope' not in baseline['config']['Session']
    baseline['config']['Session']['NudgeQueueScope'] = ''
    result['config.baseline.json'] = (json.dumps(baseline, sort_keys=True, indent=2)+'\n').encode()
    return result


def scoped_overlay(raw):
    before = tomllib.loads(raw.decode())
    assert 'nudge_queue_scope' not in before['session'], 'already scoped input'
    marker = b'[session]\n'
    assert raw.count(marker) == 1, 'ambiguous session table'
    changed = raw.replace(marker, marker+b'nudge_queue_scope = "session-epoch"\n')
    expected = copy.deepcopy(before)
    expected['session']['nudge_queue_scope'] = 'session-epoch'
    assert tomllib.loads(changed.decode()) == expected, 'unexpected scope delta'
    return changed


def scoped_config(value):
    assert value['config']['Session']['NudgeQueueScope'] == '', 'non-baseline queue scope'
    changed = copy.deepcopy(value)
    changed['config']['Session']['NudgeQueueScope'] = 'session-epoch'
    return changed


def prove_completed_inputs(old):
    w = json.loads(old.read(WORKTREE, WORKTREE_SHA))
    assert w['worktree'] == WORK and w['branch'] == 'codex/ga-mb91-c1-package'
    assert w['base'] == '801a5a9d5b0d72f665c949a86573357f02c9f1ac'
    assert all(w.get(k) is True for k in ('ok', 'tracked_clean', 'default_rules_unchanged'))
    assert w['worker_launched'] is False and w['execution_authorized_by_this_result'] is False
    t = json.loads(old.read(TERMINAL, TERMINAL_SHA))
    assert all(t.get(k) is True for k in ('ok', 'actual_host_verified',
        'terminal_suspension_endpoint_bound', 'accepted_restoration_bound'))
    c = json.loads(old.read(CLOSE, CLOSE_SHA))
    assert c == dict(ok=True, closed_session='ci-mzoxg', open_sessions=0,
        city_tmux_sessions=0, worktree_processes=0, tmux_server_killed=False,
        signals_sent=False,
        executor_sha256='fb7e9dd7221bdba1936eedd7ffc4482d0595486b3155cbb0c3c39479f144d7cb')


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
    # Exact merged and adopted Core PR50 and finalized P14 inputs; no rebuild,
    # installation, revision waiver or receipt fabrication occurs in PREP.
    old.GC_SHA = '5802a35645280790f1cda16dff3c71445be7146e42021f3be5fd481e79138444'
    old.COMPOSE = Path('/var/tmp/ga-e0t1.22-p14-candidate-compose-diagnostic-20260930/compose')
    old.COMPOSE_SHA = 'f5c9d7a19b68efaf93e449002ba13772ba218646a0be9d833a98479b0c2857f6'
    old.BUILD = Path('/var/tmp/ga-e0t1.22-p14-preflight-diagnostic-20260930')
    old.FINALIZE_SHA = '5b9e8dfee6a795ffefdf1d9ec6e95da38bb30f2bd5c7868f732bb3192bacf626'
    old.PRIOR = Path('/var/tmp/ga-e0t1.22-p14-input-20260930/receipt.input.draft.json')
    old.PRIOR_SHA = '9d2cb1b2b21150594d9ccd3bec35d69ed092c6074e51b774e018fb9debcc53b4'
    old.RECEIPT_SHA = '2607e90522b5571a5180d882e3d21882bafbc42423e0855f11fae7ec00bdf980'
    old.read(PROMPT, PROMPT_SHA)
    old.read(HERE/'WORKER-BRIEF.md', BRIEF_SHA)
    old.read(HERE/'FILE-SCOPE.json', SCOPE_SHA)
    old.read(HERE/'PRESERVED-PARTIAL-INPUT.json',
        'f2637be8acc632bd220dd924b7765b7d6db3b0b4caf1fd4dcceabbc6b1c0a008')
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
        changed = scoped_overlay(changed)
        old.OVERLAY_SHA = old.sha(changed)
        return changed, patches, names, target, selected

    def expected(*args):
        value = original_expected(*args)
        changed = copy.deepcopy(value)
        [target] = [a for a in changed['config']['Agents'] if (a['Dir'], a['Name']) == ('gascity', 'codex')]
        target['PromptTemplate'] = str(PROMPT)
        helper.config_delta(value, changed, str(PROMPT))
        return scoped_config(changed)

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
            data = dict(data, task='ga-mb91', worktree=WORK, prompt_path=str(PROMPT),
                worker_brief_sha256=BRIEF_SHA, file_scope_sha256=SCOPE_SHA,
                prompt_sha256=PROMPT_SHA, worker_probe_sha256=PROBE_SHA,
                completed_worktree_sha256=WORKTREE_SHA, prior_terminal_sha256=TERMINAL_SHA,
                prior_close_sha256=CLOSE_SHA, permission_capture_sha256=permissions.RESULT_SHA,
                preserved_transcript_sha256=permissions.TRANSCRIPT_SHA)
            data['nudge_queue_scope'] = 'session-epoch'
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
