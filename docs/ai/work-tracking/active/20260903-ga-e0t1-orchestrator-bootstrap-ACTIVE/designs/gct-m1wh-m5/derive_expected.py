"""Derive the M5 expected constants from Git objects and current live files. Read-only."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

TEMPLATE = '/home/loucmane/gas-city-template'
COMMIT = '28539934fa742056e0a65710d5638ff559a21175'
AUTH = '/home/loucmane/gas-city-template-worktrees/gct-m1wh-pr69-authority'
CITY = Path('/home/loucmane/gascity/city')
CLI_NEW = '1e08503dbdf3c2cb0d706d32f3408277388d1c76ef108673e8fe42c1b322925b'
STAGED = Path('/home/loucmane/.local/share/gas-city-staging/gct-er3h/claude-2.1.280')


def git(*args, text=True):
    return subprocess.run(['git', '-C', TEMPLATE, *args], capture_output=True, text=text, check=True).stdout


def blob(commit, path):
    return git('show', commit + ':' + path, text=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def deps_version(parser_sha, cli_sha, commit):
    root = TEMPLATE
    paths = [
        ('/home/loucmane/gascity/bin/claude', cli_sha),
        (root + '/templates/claude/core-signing-control-policy.json',
         sha(blob(commit, 'templates/claude/core-signing-control-policy.json'))),
        (root + '/bin/gct-claude-signing-worker', sha(blob(commit, 'bin/gct-claude-signing-worker'))),
        (root + '/lib/gct_claude_signing_worker.py', parser_sha),
        (root + '/lib/gct_claude_subscription.py', sha(blob(commit, 'lib/gct_claude_subscription.py'))),
        (root + '/templates/claude/signing-provider.toml', sha(blob(commit, 'templates/claude/signing-provider.toml'))),
    ]
    records = [dict(path=p, sha256=d) for p, d in paths]
    domain = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return 'gct-claude-signing-worker 1 dependencies_sha256=' + sha(domain)


def coverage():
    rows = []
    for line in git('ls-tree', '-r', '--full-tree', COMMIT).splitlines():
        meta, path = line.split('\t', 1)
        mode, kind, obj = meta.split()
        rows.append((mode, path, obj))
    links = {p for m, p, _ in rows if m == '120000'}
    ancestors = set()
    for p in links:
        parts = p.split('/')
        for i in range(1, len(parts)):
            ancestors.add('/'.join(parts[:i]))
    inputs, trees, out_links = [], [], []
    seen = set()
    for mode, path, obj in sorted(rows, key=lambda r: r[1]):
        parts = path.split('/')
        if mode == '120000':
            out_links.append(dict(path=path, target=blob(COMMIT, path).decode()))
            continue
        chosen = next(('/'.join(parts[:i]) for i in range(1, len(parts))
                       if '/'.join(parts[:i]) not in ancestors), None)
        if chosen is None:
            inputs.append(dict(path=path, sha256=sha(blob(COMMIT, path)),
                               mode=493 if mode == '100755' else 420))
        elif chosen not in seen:
            seen.add(chosen)
            trees.append(dict(path=chosen, mode=493))
    pointer = ('gitdir: ' + TEMPLATE + '/.git/worktrees/' + Path(AUTH).name + '\n').encode()
    inputs.append(dict(path='.git', sha256=sha(pointer), mode=420))
    return dict(inputs=inputs, trees=trees, links=out_links, tracked=len(rows))


CITY_EDITS = {
    21: ('model = "opus-5"\n', 'model = "opus-5-5"\n'),
    28: ('default = "opus-5"\n', 'default = "opus-5-5"\n'),
    31: ('value = "opus-5"\n', 'value = "opus-5-5"\n'),
    32: ('label = "Claude Opus 5"\n', 'label = "Claude Opus 5.5"\n'),
    33: ('flag_args = ["--model", "claude-opus-5"]\n', 'flag_args = ["--model", "claude-opus-5-5"]\n'),
    236: ('model = "opus-5"\n', 'model = "opus-5-5"\n'),
}
RIGPERM_EDITS = {95: ('model = "opus-5"\n', 'model = "opus-5-5"\n')}


def edited(path, edits):
    lines = Path(path).read_bytes().decode().splitlines(True)
    for number, (old, new) in edits.items():
        assert lines[number - 1] == old, (path, number, lines[number - 1])
        lines[number - 1] = new
    return ''.join(lines).encode()


def main():
    assert git('rev-parse', COMMIT).strip() == COMMIT
    assert sha(STAGED.read_bytes()) == CLI_NEW
    # Method check: reproduce the recorded R9 and M3 worker versions.
    parser_old = 'bac4df82f58459973d383a0467c1238e27e9dbc405ac37acf6719d05111c13e1'
    parser_m3 = '4f9acd546431f865c2b0bddeec81a4b2bbb7381a32a99b5dd93a155b6be7dcb4'
    cli_old = '26d020351e8112f4006790f3cfce43b4c9df0c1bb1d0e542364d64151b81d5ba'
    m3 = deps_version(parser_m3, cli_old, '51440da2d0ff12912ff7d2ec26d239849e3bc342')
    assert m3.endswith('8b8b3f7680181c1bad5ee74f6773e8c57616531e3bf16b94649c94bc0f9766a5'), m3
    parser_new = sha(blob(COMMIT, 'lib/gct_claude_signing_worker.py'))
    city_new = edited(CITY / 'city.toml', CITY_EDITS)
    rig_new = edited(CITY / 'managed/rig-permissions.toml', RIGPERM_EDITS)
    out = dict(
        commit=COMMIT, authority=AUTH, parser_old=parser_old, parser_new=parser_new,
        cli_old=cli_old, cli_new=CLI_NEW,
        claude_native_version_old='2.1.263 (Claude Code)', claude_native_version_new='2.1.280 (Claude Code)',
        worker_version_old_r9='gct-claude-signing-worker 1 dependencies_sha256=b7fee4467e83c7c9d07c2c421142f20297ad1cd3de93192713400aa01d8714b0',
        worker_version_m3=m3, worker_version_new=deps_version(parser_new, CLI_NEW, COMMIT),
        city_old=sha((CITY / 'city.toml').read_bytes()), city_new=sha(city_new),
        rigperm_old=sha((CITY / 'managed/rig-permissions.toml').read_bytes()), rigperm_new=sha(rig_new),
        coverage=coverage())
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
    Path(sys.argv[2]).write_bytes(city_new)
    Path(sys.argv[3]).write_bytes(rig_new)
    print(json.dumps({k: v for k, v in out.items() if k != 'coverage'}, indent=1))
    print({k: len(v) if isinstance(v, list) else v for k, v in out['coverage'].items()})


if __name__ == '__main__':
    main()
