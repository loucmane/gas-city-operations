"""Live M10 prerequisite (ga-bebv S3): install the replace-mode city.toml, one guarded step per invocation.

  python3 -I -B prereqs_m10.py <manifest_candidate.py sha256> <step>
  python3 -I -B prereqs_m10.py <manifest_candidate.py sha256> resume <step>
  python3 -I -B prereqs_m10.py <manifest_candidate.py sha256> rollback

Steps run in this order:
- inputs: no live change. Derives the new city.toml from the installed bytes with make_city.py (4f7e170f ->
  e5b68c40), proves its structure (below) and writes it as reports/m10-inputs/city.toml, the source M10 names
  for city-config. The previous bytes are already backed up as reports/m6-inputs/city.toml.before, which M10
  keeps as the city-config backup; this step proves that file too.
- city: replaces the installed city.toml with those bytes (a fresh temporary file, then an atomic rename).

Metadata-only adoption (Core metadata_adopt.go) refuses unless every managed file is already installed and its
previous bytes are backed up, so this runs before the M10 capture, exactly as M5 installed its city.toml.

Every step binds the reviewed candidate bytes, waits for a natural reconciler quiet slot (never starting,
stopping or signalling the timer), proves the quiet host (the sequence 16 accepted host and dolt-aware scope, no
city tmux, the sequence 16 suspension record 6d89f537) and its exact predecessor, writes an intent, performs one
bounded change, and records the exact postcondition under reports/m10-inputs. An interrupted step can only
`resume`, which proves the postcondition and never repeats the change.

The structure proof (city_structure) parses both documents and requires that the new one equals the old one
except that [providers.claude] and [providers.codex] are exactly the two reviewed fragments and exactly the
eight reviewed [[patches.agent]] work_dir_roots entries are appended. It also requires (selections) that every
option a claude- or codex-family selection names in city.toml, the three managed fragments or an agent.toml is
still offered after the change. The full resolution with the deployed Core source is the offline probe in
PLAN-M10.md; this is the live guard against drift since that probe.

`rollback` restores the installed city.toml from reports/m6-inputs/city.toml.before (4f7e170f). It runs only
while the installed manifest is still M9 and no M10 executor window may hold the timer paused or may have
launched an apply. Each attempt writes through a fresh temporary name.

No gc, lifecycle, timer, worker, signer or Bead action. The Obsidian reconciler timer is never touched.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tomllib
import types

HERE = Path(__file__).parent
PREREQS = HERE.parent.parent/'ga-e0t1.15-deploy/s3/prereqs_m6.py'
PREREQS_SHA = 'a36824b89d6feb23a6d9a7ade26127c4848e71df6e4a0f525e308b0f02bd006e'
RUNTIME_SHA = '2585357a808d8f36604d4bf45a39a5363ba87c8d719413ba42d9fd0fac71973f'  # source_runtime.py
CLOSURE_SHA = 'ce310593418e30b89f08645824c6cdd5b700fcff60b12f688fffc3d42d31d5d8'  # metadata_closure.py (M7 bytes)
SEQ16 = Path('/var/tmp/ga-bebv-seq16-20260927/postflight2.json')
SEQ16_SHA = '999051582a8eb874016fa8efdf43757e7d43ad94ac07797cb78fbbe1edfdafad'
CITY = Path('/home/loucmane/gascity/city')
FRAGMENTS = ('managed/rig-permissions.toml', 'managed/attention-funnel.toml', 'managed/core-signing-continuity.toml')
STEPS = ('inputs', 'city')
PATCH_COUNT = 8


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path, expected, name):
    raw = Path(path).read_bytes()
    require(expected is not None and digest(raw) == expected, str(path) + ' differs from the reviewed digest')
    module = types.ModuleType(name); module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def city_structure(old_text, new_text):
    """Pure: the new document is the old one with exactly the reviewed provider and patch changes."""
    old, new = tomllib.loads(old_text), tomllib.loads(new_text)
    claude = tomllib.loads((HERE/'providers-claude.toml').read_text())['providers']['claude']
    codex = tomllib.loads((HERE/'providers-codex.toml').read_text())['providers']['codex']
    patches = tomllib.loads((HERE/'patches-work-dir-roots.toml').read_text())['patches']['agent']
    require(len(patches) == PATCH_COUNT and all(set(p) == {'dir', 'name', 'work_dir_roots'} for p in patches),
            'reviewed work_dir_roots patches')
    require(new['providers']['claude'] == claude and new['providers']['codex'] == codex, 'replaced providers')
    for name, spec in (('claude', claude), ('codex', codex)):
        require(spec['options_schema_merge'] == 'replace', name + ' merge mode')
        keys = [o['key'] for o in spec['options_schema']]
        require(len(keys) == len(set(keys)), name + ' duplicate schema key')
        for option in spec['options_schema']:
            values = [c['value'] for c in option['choices']]
            require(len(values) == len(set(values)) and option['default'] in values, name + ' schema ' + option['key'])
        for key, value in spec['option_defaults'].items():
            option = [o for o in spec['options_schema'] if o['key'] == key]
            require(len(option) == 1 and option[0]['default'] == value, name + ' default ' + key)
        flags = json.dumps(spec)
        for unsafe in ('dangerously', 'bypassPermissions', '--yolo', 'danger-full-access', 'acceptEdits'):
            require(unsafe not in flags, name + ' offers an unrestricted choice: ' + unsafe)
    rest_old = {k: v for k, v in old.items() if k not in ('providers', 'patches')}
    rest_new = {k: v for k, v in new.items() if k not in ('providers', 'patches')}
    require(rest_old == rest_new, 'city.toml changed outside providers and patches')
    others = lambda doc: {k: v for k, v in doc['providers'].items() if k not in ('claude', 'codex')}
    require(others(old) == others(new), 'another provider changed')
    require({k: v for k, v in new['patches'].items() if k != 'agent'} ==
            {k: v for k, v in old['patches'].items() if k != 'agent'}
            and new['patches']['agent'] == old['patches']['agent'] + patches, 'patches changed beyond the append')
    return dict(patches=len(patches), claude_keys=[o['key'] for o in claude['options_schema']],
                codex_keys=[o['key'] for o in codex['options_schema']])


def selections(city_text, fragment_texts, agent_texts):
    """Pure: every option a claude- or codex-family selection names is offered by its provider's schema.

    A provider with its own options_schema and options_schema_merge "by_key" overlays its parent's schema key by
    key; with any other merge mode its own schema replaces the parent's. A provider without an options_schema
    inherits its parent's. Selections: every provider's option_defaults, city rig overrides, [[patches.agent]] in
    city.toml and the managed fragments, and agent.toml option_defaults. An agent.toml without a provider uses
    workspace.provider; an override or patch without one is checked against every family provider (below).
    """
    city = tomllib.loads(city_text)
    providers = dict(city.get('providers', {}))
    documents = [('city', city)]
    for name, text in sorted(fragment_texts.items()):
        document = tomllib.loads(text)
        providers.update(document.get('providers', {}))
        documents.append((name, document))
    default_provider = city.get('workspace', {}).get('provider', '')

    def schema(name, seen=()):
        require(name not in seen, 'provider base cycle: ' + name)
        spec = providers.get(name, {})
        own = {o['key']: [c['value'] for c in o['choices']] for o in spec.get('options_schema', [])}
        base = spec.get('base', '')
        if base.startswith('provider:'):
            parent = schema(base[len('provider:'):], seen + (name,))
            if parent is None:
                return None
            if not own:
                return parent
            return dict(parent, **own) if spec.get('options_schema_merge') == 'by_key' else own
        return own if name in ('claude', 'codex') else None

    selected, missing = {}, {}
    # A rig override or agent patch without a provider applies to an agent whose provider is declared elsewhere
    # (its agent.toml or pack). Such a selection must be offered by at least one claude- or codex-family
    # provider; the offline Core probe resolves it exactly.
    union = {}
    for name in providers:
        for key, values in (schema(name) or {}).items():
            union.setdefault(key, set()).update(values)

    def check(origin, provider, defaults):
        offered = union if provider is None else schema(provider)
        if offered is None or not defaults:
            return
        selected[origin] = dict(provider=provider, defaults=defaults)
        for key, value in defaults.items():
            if value not in offered.get(key, ()):
                missing[origin + '.' + key] = value

    for name, spec in sorted(providers.items()):
        check('providers.' + name, name, spec.get('option_defaults', {}))
    for row in city.get('rigs', []):
        for index, override in enumerate(row.get('overrides', [])):
            check('rigs.%s.overrides.%d' % (row['name'], index), override.get('provider'),
                  override.get('option_defaults', {}))
    for origin, document in documents:
        for index, patch in enumerate(document.get('patches', {}).get('agent', [])):
            check('%s.patches.agent.%d' % (origin, index), patch.get('provider'), patch.get('option_defaults', {}))
    for path, text in sorted(agent_texts.items()):
        agent = tomllib.loads(text)
        check(path, agent.get('provider', default_provider), agent.get('option_defaults', {}))
    require(not missing, 'a selection names an option the providers no longer offer: ' + json.dumps(missing))
    return dict(selected=len(selected), origins=sorted(selected))


def live_texts():
    fragments = {name: (CITY/name).read_text() for name in FRAGMENTS}
    agents = {str(p): p.read_text() for p in sorted((CITY/'agents').glob('*/agent.toml'))}
    return fragments, agents


class Context:
    def __init__(self, expected):
        self.p = load(PREREQS, PREREQS_SHA, 'm6_prereqs_helpers')
        self.m = load(HERE/'manifest_candidate.py', expected, 'm10_candidate')
        # The generator is not digest-pinned here: derive() refuses unless its output is exactly CITY_NEW,
        # and the check below binds that constant to the reviewed candidate's.
        raw = (HERE/'make_city.py').read_bytes()
        self.make = load(HERE/'make_city.py', digest(raw), 'm10_make_city')
        self.expected = expected
        self.inputs = Path(self.m.O + '/reports/m10-inputs')
        graph = load(HERE/'source_runtime.py', RUNTIME_SHA, 'pinned_runtime').legacy()
        self.o, self.s = graph['observe_recovery'], graph['recovery_state']
        load(HERE/'metadata_closure.py', CLOSURE_SHA, 'm10_closure').install_policy(self.o, self.s,
                                                                                    self.m.WATCHDOG_IMAGE)
        self.o.GC_SHA = self.m.NEW
        raw = SEQ16.read_bytes()
        require(digest(raw) == SEQ16_SHA, 'sequence 16 accepted observation drift')
        self.seq16 = json.loads(raw)['closure']
        require(self.make.CITY_OLD == self.m.CITY_OLD and self.make.CITY_NEW == self.m.CITY_NEW,
                'generator and candidate disagree on the city digests')

    def quiet(self):
        slot = self.p.quiet_slot()
        host = self.o.host_observation()
        require(host == self.seq16['host'], 'host is not the sequence 16 accepted epoch')
        scope = self.s.quiet_scope(host)
        require(scope == self.seq16['scope'], 'scope is not the sequence 16 accepted scope')
        require(self.p.sha(self.p.SUSPENSION) == self.m.SUSPENSION_SHA, 'suspension record drift')
        return dict(host=host, scope=scope, suspension_sha256=self.m.SUSPENSION_SHA, reconciler=slot)

    def executor_closed(self):
        """False while an M10 executor window may hold the timer paused or may have launched an apply."""
        root = Path(self.m.ROOT)
        if not os.path.lexists(root):
            return True
        q = root/'q'
        if os.path.lexists(q/'commit-consumed.json'):
            return False
        if os.path.lexists(q/'restored.json'):
            return True
        return not os.path.lexists(q/'preparation-pause-intent.json')

    def record_path(self, step, suffix=''):
        return self.inputs/('prereq-' + step + suffix + '.json')

    def common(self, step):
        p = self.p
        require(p.sha(p.INSTALLED) == self.m.OLD_MANIFEST_SHA and p.sha(p.INSTALLED_RECEIPT) == self.m.OLD_RECEIPT_SHA,
                'installed platform metadata is not the M9 pair')
        require(not os.path.lexists(self.m.ROOT), 'M10 package root already exists')
        require(not os.path.lexists(self.m.O + '/reports/m10-capture'), 'M10 capture already exists')
        require(not os.path.lexists(self.inputs/'rollback.json'), 'rollback consumed; start a new package')
        require(not os.path.lexists(self.record_path(step)), 'step already consumed: ' + step)
        for earlier in STEPS[:STEPS.index(step)]:
            require(os.path.lexists(self.record_path(earlier)), 'earlier step missing: ' + earlier)

    def begin(self, step):
        self.common(step)
        require(not os.path.lexists(self.record_path(step, '.intent')),
                'step interrupted after its intent; use resume ' + step)
        return self.quiet()

    def intent(self, step, before):
        self.p.write_exclusive(self.record_path(step, '.intent'), self.p.encoded(dict(
            step=step, candidate_sha256=self.expected, quiet_before=before)), 0o600)

    def finish(self, step, before, value, resumed=False):
        after = self.quiet()
        require(after['host'] == before['host'], 'host identity changed during the step')
        value = dict(value, step=step, bead='ga-bebv', candidate_sha256=self.expected, resumed=resumed,
                     live_mutation=step != 'inputs', quiet_before=before, quiet_after=after)
        self.p.write_exclusive(self.record_path(step), self.p.encoded(value), 0o600)
        print(json.dumps(dict(step=step, ok=True, resumed=resumed, record=str(self.record_path(step)))))

    def backup(self):
        require(self.p.identity(self.m.CITY_CONFIG_BACKUP) == self.p.owned(self.m.CITY_OLD, 0o644),
                'city-config backup identity')
        return self.p.identity(self.m.CITY_CONFIG_BACKUP)


def temporary(operation, attempt=0):
    suffix = '.%d' % attempt if attempt else ''
    return CITY/('.city.toml.ga-bebv-m10.' + operation + suffix + '.tmp')


def replace_atomic(p, data, operation):
    """Write through a fresh temporary file in the city directory, then rename over city.toml."""
    if operation == 'forward':
        tmp = temporary('forward')
    else:
        tmp = next((temporary('rollback', n) for n in range(1, 10) if not os.path.lexists(temporary('rollback', n))),
                   None)
        require(tmp is not None, 'nine rollback attempts left temporaries; inspect ' + str(CITY))
    require(not os.path.lexists(tmp), 'leftover temporary file needs inspection: ' + str(tmp))
    p.write_exclusive(tmp, data, 0o644)
    os.replace(tmp, CITY/'city.toml')
    p.fsync_dir(CITY)


def post_inputs(c):
    source = c.p.identity(c.m.CITY_SOURCE)
    require(Path(c.m.CITY_SOURCE) == c.inputs/'city.toml' and source == c.p.owned(c.m.CITY_NEW, 0o644),
            'city source identity')
    return dict(source=source, backup=c.backup())


def post_city(c):
    live = c.p.identity(CITY/'city.toml')
    require(live == c.p.owned(c.m.CITY_NEW, 0o644), 'installed city identity')
    require(not os.path.lexists(temporary('forward')), 'forward temporary left behind')
    fragments, agents = live_texts()
    return dict(after=live, selections=selections((CITY/'city.toml').read_text(), fragments, agents))


POST = {'inputs': post_inputs, 'city': post_city}


def step_inputs(c):
    c.common('inputs')
    # An empty, owner-only, real directory is what an interruption between mkdir and the intent leaves.
    if os.path.lexists(c.inputs):
        st = os.lstat(c.inputs)
        require(os.path.isdir(c.inputs) and not os.path.islink(c.inputs) and (st.st_mode & 0o7777) == 0o700
                and st.st_uid == os.geteuid() and not any(c.inputs.iterdir()), 'inputs directory already exists')
    old = (CITY/'city.toml').read_bytes()
    require(c.p.identity(CITY/'city.toml') == c.p.owned(c.m.CITY_OLD, 0o644), 'live city predecessor identity')
    new = c.make.derive(old)
    structure = city_structure(old.decode(), new.decode())
    fragments, agents = live_texts()
    # Only the new document: its claude and codex schemas are complete (replace mode), while the installed
    # by_key providers inherit builtin schemas this parser cannot see.
    after_selections = selections(new.decode(), fragments, agents)
    backup = c.backup()
    before = c.quiet()
    if not os.path.lexists(c.inputs):
        os.mkdir(c.inputs, 0o700)
        c.p.fsync_dir(c.inputs.parent)
    c.intent('inputs', before)
    c.p.write_exclusive(c.inputs/'city.toml', new, 0o644)
    c.finish('inputs', before, dict(post_inputs(c), structure=structure, backup=backup,
                                    selections_candidate=after_selections))


def step_city(c):
    before = c.begin('city')
    path = CITY/'city.toml'
    require(c.p.identity(path) == c.p.owned(c.m.CITY_OLD, 0o644), 'live city predecessor identity')
    data = Path(c.m.CITY_SOURCE).read_bytes()
    require(digest(data) == c.m.CITY_NEW, 'city source bytes')
    structure = city_structure(path.read_text(), data.decode())
    fragments, agents = live_texts()
    candidate = selections(data.decode(), fragments, agents)
    c.backup()
    require(not os.path.lexists(temporary('forward')), 'leftover temporary file needs inspection')
    c.intent('city', before)
    replace_atomic(c.p, data, 'forward')
    c.finish('city', before, dict(post_city(c), before_sha256=c.m.CITY_OLD, structure=structure,
                                  selections_candidate=candidate))


def resume(c, step):
    """Record an interrupted step only when its exact reviewed postcondition already holds."""
    require(step in STEPS, 'unknown step')
    c.common(step)
    intent = c.record_path(step, '.intent')
    require(os.path.lexists(intent), 'no interrupted intent for ' + step)
    recorded = json.loads(intent.read_text())
    require(recorded.get('step') == step and recorded.get('candidate_sha256') == c.expected,
            'intent belongs to another step or candidate')
    verified = POST[step](c)
    c.finish(step, recorded['quiet_before'], dict(verified, resumed_from_intent=str(intent)), resumed=True)


def rollback(c):
    p = c.p
    require(p.sha(p.INSTALLED) == c.m.OLD_MANIFEST_SHA, 'successor may be installed; rollback refused')
    require(c.executor_closed(), 'M10 executor window is open; restore it through the executor first')
    require(os.path.isdir(c.inputs) and not os.path.lexists(c.inputs/'rollback.json'), 'rollback state')
    try:
        observed = c.quiet()
    except Exception as exc:  # restoration must remain possible; record why the host was not quiet
        observed = dict(error=type(exc).__name__, reason=str(exc))
    actions = []
    live = p.sha(CITY/'city.toml')
    require(live in (c.m.CITY_OLD, c.m.CITY_NEW), 'unknown installed city.toml; inspect by hand')
    if live != c.m.CITY_OLD:
        data = Path(c.m.CITY_CONFIG_BACKUP).read_bytes()
        require(digest(data) == c.m.CITY_OLD, 'backup bytes differ: ' + c.m.CITY_CONFIG_BACKUP)
        replace_atomic(p, data, 'rollback')
        actions.append('city.toml')
    require(p.identity(CITY/'city.toml') == p.owned(c.m.CITY_OLD, 0o644), 'rollback postcondition')
    leftovers = sorted(str(x) for x in CITY.glob('.city.toml.ga-bebv-m10.*.tmp'))
    value = dict(actions=actions, candidate_sha256=c.expected, quiet=observed, leftovers=leftovers,
                 source_left_in_place=os.path.lexists(c.m.CITY_SOURCE))
    p.write_exclusive(c.inputs/'rollback.json', p.encoded(value), 0o600)
    print(json.dumps(dict(rollback=actions, ok=True, leftovers=leftovers)))


ACTIONS = {'inputs': step_inputs, 'city': step_city, 'rollback': rollback}


def main():
    require(sys.flags.isolated and sys.flags.dont_write_bytecode and os.geteuid() == 1000,
            'isolated source-only UID1000 invocation required')
    args = sys.argv[1:]
    require(len(args) in (2, 3) and len(args[0]) == 64
            and ((len(args) == 2 and args[1] in ACTIONS) or (len(args) == 3 and args[1] == 'resume'
                                                            and args[2] in STEPS)),
            'usage: prereqs_m10.py <candidate sha256> <step>|resume <step>|rollback')
    os.umask(0o022)
    context = Context(args[0])
    if args[1] == 'resume':
        resume(context, args[2])
    else:
        ACTIONS[args[1]](context)


if __name__ == '__main__':
    main()
