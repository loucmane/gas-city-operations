"""S1 only: native-finalize an uninstalled isolation image from the existing P13 receipt.

Uses S5's digest-bound reader, confined observation, owned normalize/finalize phases,
exact receipt-delta check and unchanged-host check. No BIND/STAGE/ROUTE/RESUME entry.
"""
import copy
import base64
import hashlib
import json
from pathlib import Path
import sys
import tomllib
import types

HERE = Path(__file__).parent
O = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap')
S5 = O/'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-e8ex-window/prep-r11.py'
S5_SHA = '6cd7c219338c46607f1fbf53a5aad6e92383062f35e76c546e1aab997ea07322'
PINS = {
    'city.window-r2.toml': 'dfa4d979a27c9b8d5fe8a21c5bfbb9bb425fdc6e5848647454dd02d3d9d8cdae',
    'window-r2-declared-delta.json': '4bea8b42e4b85f9444f0097304c16c588618ca587aa83424cd7b0c8784dfdcc6',
    'config.baseline.json': '2440317ed9832d69e7bfd4766f65eda54e9337b7f36626ca6cc8fee34fbb47ca',
    'orders.baseline.json': '96d2952125d9ff3b5d986f77929c581691b604d58fec62f95cc1edcf6fb607b3',
}
WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
OPTIONS = dict(model='gpt-6-astra', effort='high', permission_mode='fail-fast',
               worklog_access='operations-candidate-only')
REVISION_AFTER = '9b6e94d8ecba8baa9b550fbb19a62891c0cf8edb033520adbbe964c0eff3999f'
MCP_ARGS = ['-c', 'mcp_servers.serena.enabled=false', '-c', 'mcp_servers.aegis.enabled=false']
RESUME = ("/home/loucmane/gascity/bin/codex resume --model gpt-6-astra -c model_reasoning_effort=high "
          "--ask-for-approval never --sandbox workspace-write -c "
          "'sandbox_workspace_write.writable_roots=[\"" + WORK + "\"]' "
          "-c mcp_servers.serena.enabled=false -c mcp_servers.aegis.enabled=false {{.SessionKey}}")


def load():
    raw = S5.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == S5_SHA, 'S5 source drift'
    old = types.ModuleType('s5_preparation')
    old.__file__ = str(S5)
    exec(compile(raw, str(S5), 'exec', dont_inherit=True), old.__dict__)
    return old


def inputs(old):
    data = json.loads(old.read(HERE/'inputs.json'))
    assert set(data) == set(PINS) | {'city.window-r3.toml', 'window-restrictions.rules'}
    raw = {name: base64.b64decode(value, validate=True) for name, value in data.items()}
    for name, digest in PINS.items():
        assert hashlib.sha256(raw[name]).hexdigest() == digest, name
    return raw


def expected_config(baseline, declared):
    value = copy.deepcopy(baseline)
    cfg = value['config']
    patches = {(x['dir'], x['name']): x for x in declared['patches']}
    assert len(patches) == len(declared['patches']) == 48
    names = {(a['Dir'], a['Name']) for a in cfg['Agents']}
    assert len(names) == len(cfg['Agents']) == 114 and set(patches) <= names
    fields = dict(suspended='Suspended', work_dir='WorkDir', work_dir_roots='WorkDirRoots',
                  min_active_sessions='MinActiveSessions', max_active_sessions='MaxActiveSessions')
    for a in cfg['Agents']:
        identity = (a['Dir'], a['Name'])
        for key, target in fields.items():
            if key in patches.get(identity, {}):
                a[target] = patches[identity][key]
        if identity == ('gascity', 'codex'):
            a['Provider'] = 'codex-managed'
            a['OptionDefaults'] = OPTIONS.copy()
            a['Env'] = dict(PATH='/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin',
                            GC_HOME='/home/loucmane/gascity/home', GIT_OPTIONAL_LOCKS='0')
            assert a['WorkDir'] == WORK and a['WorkDirRoots'] == [WORK]
    p = cfg['Providers']['codex-managed']
    p.update(OptionsSchemaMerge='replace', PrintArgs=[], OptionDefaults=OPTIONS.copy(),
             ArgsAppend=MCP_ARGS.copy(), ResumeCommand=RESUME)
    cfg['Workspace']['MaxActiveSessions'] = 1
    assert cfg['Orders']['Overrides'] is None
    cfg['Orders']['Skip'] = declared['order_skip']
    cfg['Orders']['Overrides'] = [dict(Name='nudge-on-route', Rig='', Enabled=None, Trigger=None,
        Gate=None, Interval=None, Schedule=None, Check=None, On=None, Pool=None, Timeout=None,
        CheckTimeout=None, Idempotent=None, Env=declared['nudge_env'])]
    warning = ('agent "gascity/codex": max_active_sessions=1 creates a canonical singleton that '
               'drains when scale_check returns 0; declare [[named_session]] only if you need a '
               'session that survives empty-demand windows')
    assert warning not in value['validation']['warnings']
    value['validation']['warnings'] = sorted([*value['validation']['warnings'], warning])
    assert all(a['Suspended'] for a in cfg['Agents'] if a['Provider'] == 'codex-managed'
               and (a['Dir'], a['Name']) != ('gascity', 'codex'))
    return value


def configure(old):
    frozen = inputs(old)
    baseline = json.loads(frozen['config.baseline.json'])
    orders = json.loads(frozen['orders.baseline.json'])
    declared = json.loads(frozen['window-r2-declared-delta.json'])
    old_line = b'[providers.codex-managed]\nbase = "provider:codex"\n'
    new_line = old_line + ('args_append = '+json.dumps(MCP_ARGS)+'\nresume_command = '+json.dumps(RESUME)+'\n').encode()
    assert frozen['city.window-r2.toml'].count(old_line) == 1
    overlay = frozen['city.window-r2.toml'].replace(old_line, new_line)
    assert frozen['city.window-r3.toml'] == overlay, 'R3 derivation drift'
    parsed = tomllib.loads(overlay.decode())
    options = parsed['providers']['codex-managed']
    assert options['options_schema_merge'] == 'replace' and options['print_args'] == []
    schema = options['options_schema']
    assert {s['key']: [c['value'] for c in s['choices']] for s in schema} == {
        key: [value] for key, value in OPTIONS.items()}
    old.ROOT = Path('/var/tmp/ga-e0t1.20-prep-20260927-r1')
    old.WORK = WORK
    old.PRIOR = Path('/var/tmp/gct-oak5-p13-input-20260927/receipt.input.draft.json')
    old.PRIOR_SHA = '7b8472f6cc339f261abc32b32e27b1d7f2a3c494ec24be021c396dbac2d9969d'
    old.CITY_SHA = 'bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1'
    old.RECEIPT_SHA = '7185414ebade17a1fdd7d485564e85f6ad8d7e0230983c21bf917f1ed27fb0ba'
    old.REVISION = 'a61666b33528c1cb8b497f55d9c6b8b37df2ce74ed9853345de8d7321e18f58f'
    old.OVERLAY_SHA = old.sha(overlay)

    def build(city, observed, observed_orders):
        assert old.sha(city) == old.CITY_SHA
        assert observed == baseline and observed_orders == orders, 'frozen input drift'
        ids = [(a['Dir'], a['Name']) for a in observed['config']['Agents']]
        selected = [ids.index((p['dir'], p['name'])) for p in declared['patches']]
        return overlay, declared['patches'], declared['order_skip'], ids.index(('gascity', 'codex')), selected

    old.build_overlay = build
    old.expected_config = lambda observed, *unused: expected_config(observed, declared)
    inherited_image = old.receipt_image

    def image(*args):
        before = json.loads(old.read(old.RECEIPT, old.RECEIPT_SHA))
        names = {p['name'] for p in before['profiles']}
        assert names == {'gascity/gc.implementation-worker', 'gascity/operations-candidate-worker',
                         'gas-city-template/gc.implementation-worker'} and len(before['profiles']) == 3
        raw = inherited_image(*args)
        final = json.loads(raw)
        assert final['profiles'] == before['profiles'], 'typed profiles changed'
        assert final['permission_revision'] == REVISION_AFTER, 'native revision drift'
        return raw

    old.receipt_image = image
    inherited_write = old.write

    def write(name, data, root=None):
        if name == 'result.json':
            data.update(only_unsuspended_city_core_agent='gascity/codex',
                        execution_authorized_by_this_result=False, preparation_only=True,
                        typed_profile_count=3)
        return inherited_write(name, data, root)

    old.write = write
    old._SOURCE_SHA = globals().get('_SOURCE_SHA')
    return old


if __name__ == '__main__':
    old = configure(load())
    assert old._SOURCE_SHA and old.read(Path(__file__), old._SOURCE_SHA), 'source launcher required'
    if len(sys.argv) == 3 and sys.argv[1] == 'normalize':
        old.normalize_main(Path(sys.argv[2]))
    else:
        assert len(sys.argv) == 1
        old.main()
