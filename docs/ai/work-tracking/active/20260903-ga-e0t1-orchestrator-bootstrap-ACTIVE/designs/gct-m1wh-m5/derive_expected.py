"""Derive the M5 expected constants from Git objects, the staged CLI and live predecessor bytes.

It writes only the output files named on its command line; it never touches live
state. It derives:
- the authority coverage from `git ls-tree` of 28539934;
- the signing-worker dependency version, after first reproducing the reviewed M3
  value;
- the transitional and final city.toml bytes;
- the registry bytes synced to the 28539934 gascity profile;
- the rig-permissions render. That uses the reviewed 28539934 renderer, run from the
  gct-er3h worktree (whose tree is identical to 28539934), with its own root path
  replaced by the canonical checkout path. The method is first checked by reproducing
  the live file from the live registry.

  python3 -I -B derive_expected.py <out-dir>
"""
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

TEMPLATE = '/home/loucmane/gas-city-template'
COMMIT = '28539934fa742056e0a65710d5638ff559a21175'
AUTH = '/home/loucmane/gas-city-template-worktrees/gct-m1wh-pr69-authority'
RENDER_ROOT = '/home/loucmane/gas-city-template-worktrees/gct-er3h-opus-5-5-worker-profiles'
RENDER_TREE = 'cfe24ca769b326ecb590dfa866e88df8dbaa3938'
CITY = Path('/home/loucmane/gascity/city')
CITY_BACKUP = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/r5/i/00')
CLI_OLD = '26d020351e8112f4006790f3cfce43b4c9df0c1bb1d0e542364d64151b81d5ba'
CLI_NEW = '1e08503dbdf3c2cb0d706d32f3408277388d1c76ef108673e8fe42c1b322925b'
STAGED = Path('/home/loucmane/.local/share/gas-city-staging/gct-er3h/claude-2.1.280')
CITY_EDITS = {
    21: ('model = "opus-5"\n', 'model = "opus-5-5"\n'),
    28: ('default = "opus-5"\n', 'default = "opus-5-5"\n'),
    31: ('value = "opus-5"\n', 'value = "opus-5-5"\n'),
    32: ('label = "Claude Opus 5"\n', 'label = "Claude Opus 5.5"\n'),
    33: ('flag_args = ["--model", "claude-opus-5"]\n', 'flag_args = ["--model", "claude-opus-5-5"]\n'),
    236: ('model = "opus-5"\n', 'model = "opus-5-5"\n'),
}
TRANSITION_AFTER = 34
TRANSITION_BLOCK = ('[[providers.claude.options_schema.choices]]\n', 'value = "opus-5-5"\n',
                    'label = "Claude Opus 5.5"\n', 'flag_args = ["--model", "claude-opus-5-5"]\n', '\n')
REGISTRY_EDITS = ((CLI_OLD, CLI_NEW), ('"2.1.263 (Claude Code)"', '"2.1.280 (Claude Code)"'))


def git(*args, text=True):
    return subprocess.run(['/usr/bin/git', '-C', TEMPLATE, *args], capture_output=True,
                          text=text, check=True).stdout


def blob(path):
    return git('show', COMMIT + ':' + path, text=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def deps_version(parser_sha, cli_sha, commit):
    def at(path):
        return sha(git('show', commit + ':' + path, text=False))
    records = [dict(path='/home/loucmane/gascity/bin/claude', sha256=cli_sha),
               dict(path=TEMPLATE + '/templates/claude/core-signing-control-policy.json',
                    sha256=at('templates/claude/core-signing-control-policy.json')),
               dict(path=TEMPLATE + '/bin/gct-claude-signing-worker', sha256=at('bin/gct-claude-signing-worker')),
               dict(path=TEMPLATE + '/lib/gct_claude_signing_worker.py', sha256=parser_sha),
               dict(path=TEMPLATE + '/lib/gct_claude_subscription.py', sha256=at('lib/gct_claude_subscription.py')),
               dict(path=TEMPLATE + '/templates/claude/signing-provider.toml',
                    sha256=at('templates/claude/signing-provider.toml'))]
    domain = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return 'gct-claude-signing-worker 1 dependencies_sha256=' + sha(domain)


def coverage():
    rows = []
    for line in git('ls-tree', '-r', '--full-tree', COMMIT).splitlines():
        meta, path = line.split('\t', 1)
        mode, _, _ = meta.split()
        rows.append((mode, path))
    links = {p for m, p in rows if m == '120000'}
    ancestors = {'/'.join(p.split('/')[:i]) for p in links for i in range(1, len(p.split('/')))}
    inputs, trees, out_links, seen = [], [], [], set()
    for mode, path in sorted(rows, key=lambda r: r[1]):
        parts = path.split('/')
        if mode == '120000':
            out_links.append(dict(path=path, target=blob(path).decode()))
            continue
        chosen = next(('/'.join(parts[:i]) for i in range(1, len(parts))
                       if '/'.join(parts[:i]) not in ancestors), None)
        if chosen is None:
            inputs.append(dict(path=path, sha256=sha(blob(path)), mode=493 if mode == '100755' else 420))
        elif chosen not in seen:
            seen.add(chosen)
            trees.append(dict(path=chosen, mode=493))
    pointer = ('gitdir: ' + TEMPLATE + '/.git/worktrees/' + Path(AUTH).name + '\n').encode()
    inputs.append(dict(path='.git', sha256=sha(pointer), mode=420))
    return dict(inputs=inputs, trees=trees, links=out_links, tracked=len(rows))


def city_bytes(raw):
    lines = raw.decode().splitlines(True)
    final = list(lines)
    for number, (before, after) in CITY_EDITS.items():
        assert final[number - 1] == before, number
        final[number - 1] = after
    assert lines[TRANSITION_AFTER - 1] == '\n' and lines[TRANSITION_AFTER - 2].startswith('flag_args')
    transition = lines[:TRANSITION_AFTER] + list(TRANSITION_BLOCK) + lines[TRANSITION_AFTER:]
    return raw, ''.join(transition).encode(), ''.join(final).encode()


def registry_bytes(raw):
    text = raw.decode()
    for before, after in REGISTRY_EDITS:
        assert text.count(before) == 1, before
        text = text.replace(before, after)
    new = text.encode()
    live, synced = json.loads(raw), json.loads(new)
    profiles = {name: json.loads((Path(RENDER_ROOT) / 'managed/profiles' / (name + '.json')).read_bytes())
                for name in ('gascity-claude-signing', 'blog-codex')}
    by_name = {r['name']: r for p in profiles.values() for r in p['rigs']}
    assert {k: v for k, v in synced.items() if k != 'rigs'} == {
        k: v for k, v in profiles['gascity-claude-signing'].items() if k != 'rigs'}
    assert all(r == by_name[r['name']] for r in synced['rigs']), 'synced registry differs from 28539934 profiles'
    assert [r for r in live['rigs'] if r['name'] == 'blog'] == [r for r in synced['rigs'] if r['name'] == 'blog']
    return raw, new


def render(registry_raw, scratch):
    head = subprocess.run(['/usr/bin/git', '-C', RENDER_ROOT, 'rev-parse', 'HEAD^{tree}'],
                          capture_output=True, text=True, check=True).stdout.strip()
    assert head == RENDER_TREE == git('rev-parse', COMMIT + '^{tree}').strip()
    status = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', RENDER_ROOT, 'status', '--porcelain',
                             '--untracked-files=normal'], capture_output=True, text=True, check=True).stdout
    assert status == '', 'renderer worktree is not clean'
    source = Path(RENDER_ROOT) / 'bin/gct-managed-rig-permissions'
    assert sha(source.read_bytes()) == sha(blob('bin/gct-managed-rig-permissions'))
    module = types.ModuleType('renderer'); module.__file__ = str(source)
    sys.modules['renderer'] = module
    exec(compile(source.read_bytes(), str(source), 'exec'), module.__dict__)
    path = Path(scratch) / 'registry.json'
    path.write_bytes(registry_raw)
    registry, _ = module._load_registry(path)
    rendered, _ = module._render(registry)
    text = rendered.decode()
    assert RENDER_ROOT + '/' in text
    return text.replace(RENDER_ROOT + '/', TEMPLATE + '/').encode()


def main():
    out = Path(sys.argv[1])
    assert git('rev-parse', COMMIT).strip() == COMMIT and sha(STAGED.read_bytes()) == CLI_NEW
    m3 = deps_version('4f9acd546431f865c2b0bddeec81a4b2bbb7381a32a99b5dd93a155b6be7dcb4', CLI_OLD,
                      '51440da2d0ff12912ff7d2ec26d239849e3bc342')
    assert m3.endswith('8b8b3f7680181c1bad5ee74f6773e8c57616531e3bf16b94649c94bc0f9766a5'), m3
    city_old, city_transition, city_final = city_bytes(CITY_BACKUP.read_bytes())
    registry_old, registry_new = registry_bytes((CITY / 'managed/rig-permissions.json').read_bytes())
    rig_live = (CITY / 'managed/rig-permissions.toml').read_bytes()
    reproduced = render(registry_old, out)
    live_lines = rig_live.decode().splitlines(True)
    assert live_lines[94] == 'model = "opus-5"\n'
    assert reproduced == ''.join(live_lines[:94] + ['model = "opus-5-5"\n'] + live_lines[95:]).encode(), \
        'method check: renderer does not reproduce the live file'
    rig_new = render(registry_new, out)
    parser_new = sha(blob('lib/gct_claude_signing_worker.py'))
    values = dict(
        commit=COMMIT, authority=AUTH, parser_new=parser_new, cli_new=CLI_NEW,
        worker_version_m3=m3, worker_version_new=deps_version(parser_new, CLI_NEW, COMMIT),
        city_old=sha(city_old), city_transition=sha(city_transition), city_new=sha(city_final),
        registry_old=sha(registry_old), registry_new=sha(registry_new),
        rigperm_old=sha(rig_live), rigperm_method_check=sha(reproduced), rigperm_new=sha(rig_new),
        retained_template_pins={p: sha(blob(p)) for p in (
            'bin/gct-claude-signing-worker', 'lib/gct_claude_subscription.py',
            'templates/claude/signing-provider.toml', 'templates/claude/core-signing-control-policy.json')},
        coverage=coverage())
    (out / 'expected.json').write_text(json.dumps(values, indent=1, sort_keys=True) + '\n')
    for name, data in (('city.toml.transition', city_transition), ('city.toml.final', city_final),
                       ('rig-permissions.json.new', registry_new), ('rig-permissions.toml.new', rig_new)):
        (out / name).write_bytes(data)
    print(json.dumps({k: v for k, v in values.items() if k != 'coverage'}, indent=1))


if __name__ == '__main__':
    main()
