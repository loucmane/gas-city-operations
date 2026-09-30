"""Derive the ga-e0t1.15 S3 metadata constants (M6) from Git objects and the live predecessor.

Read-only. It prints JSON and writes nothing. The repository argument must hold both
28539934 (the M5 Template) and cfd353f3 (the S3 target). At design time that is a
scratch clone; the live prerequisite `checkout` step re-proves the same values from the
canonical Template objects after its fetch.

Method checks first reproduce two reviewed values:
- the M5 signing-worker dependency version f36deb20, from 28539934 and CLI 1e08503d;
- the M5 authority coverage counts at 28539934 (12 inputs, 20 trees, 2 links, 277 tracked).

  python3 -I -B derive_m6.py <repository with 28539934 and cfd353f3>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

TEMPLATE = '/home/loucmane/gas-city-template'
M5_COMMIT = '28539934fa742056e0a65710d5638ff559a21175'
COMMIT = 'cfd353f30f465cdf67bbd41fab48812fe5b9617e'
M5_AUTH = '/home/loucmane/gas-city-template-worktrees/gct-m1wh-pr69-authority'
AUTH = '/home/loucmane/gas-city-template-worktrees/ga-e0t1-15-pr71-authority'
CLI = '1e08503dbdf3c2cb0d706d32f3408277388d1c76ef108673e8fe42c1b322925b'
M5_PARSER = '4e28d5b826a7471dec27e66ee3536233bbaa2ebc6ece162b4d3ca8cccd0970bd'
M5_POINTER = 'deabdafaba7ec87b78d650608707d26b80bfc5f44549a54e5488cdd52ac574be'  # M5 manifest_candidate.py AUTH_INPUTS .git
M5_VERSION = ('gct-claude-signing-worker 1 dependencies_sha256='
              'f36deb20efa5cc11781f1d9703b8e5e0d7897c6357260dff1045bcd86489ff34')
RETAINED = ('bin/gct-claude-signing-worker', 'lib/gct_claude_subscription.py',
            'templates/claude/signing-provider.toml', 'templates/claude/core-signing-control-policy.json')
CHANGED = 'lib/gct_claude_signing_worker.py'


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args, text=True):
    return subprocess.run(['/usr/bin/git', '--no-optional-locks', '-c', 'core.hooksPath=/dev/null',
                           '-C', repo, *args], capture_output=True, text=text, check=True).stdout


def blob(repo, commit, path):
    return git(repo, 'show', commit + ':' + path, text=False)


def deps_version(repo, commit, parser_sha, cli_sha):
    """The M5 derivation, unchanged: the signing worker's six dependency records."""
    def at(path):
        return sha(blob(repo, commit, path))
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


def coverage(repo, commit, authority):
    """The M5 coverage method, unchanged: maximal link-free subtrees, files, and links."""
    rows = []
    for line in git(repo, 'ls-tree', '-r', '--full-tree', commit).splitlines():
        meta, path = line.split('\t', 1)
        mode, _, _ = meta.split()
        rows.append((mode, path))
    links = {p for m, p in rows if m == '120000'}
    ancestors = {'/'.join(p.split('/')[:i]) for p in links for i in range(1, len(p.split('/')))}
    inputs, trees, out_links, seen = [], [], [], set()
    for mode, path in sorted(rows, key=lambda r: r[1]):
        parts = path.split('/')
        if mode == '120000':
            out_links.append(dict(path=path, target=blob(repo, commit, path).decode()))
            continue
        require(mode in ('100644', '100755'), 'unexpected tracked mode: ' + path)
        chosen = next(('/'.join(parts[:i]) for i in range(1, len(parts))
                       if '/'.join(parts[:i]) not in ancestors), None)
        if chosen is None:
            inputs.append(dict(path=path, sha256=sha(blob(repo, commit, path)), mode=493 if mode == '100755' else 420))
        elif chosen not in seen:
            seen.add(chosen)
            trees.append(dict(path=chosen, mode=493))
    pointer = ('gitdir: ' + TEMPLATE + '/.git/worktrees/' + Path(authority).name + '\n').encode()
    inputs.append(dict(path='.git', sha256=sha(pointer), mode=420))
    return dict(inputs=inputs, trees=trees, links=out_links, tracked=len(rows))


def derive(repo):
    require(git(repo, 'rev-parse', COMMIT + '^{commit}').strip() == COMMIT, 'target commit missing')
    require(git(repo, 'merge-base', '--is-ancestor', M5_COMMIT, COMMIT) == '', 'target does not descend from M5')
    # Method checks against reviewed M5 values.
    require(sha(blob(repo, M5_COMMIT, CHANGED)) == M5_PARSER, 'M5 parser blob')
    require(deps_version(repo, M5_COMMIT, M5_PARSER, CLI) == M5_VERSION, 'M5 version method check')
    m5 = coverage(repo, M5_COMMIT, M5_AUTH)
    require((len(m5['inputs']), len(m5['trees']), len(m5['links']), m5['tracked']) == (12, 20, 2, 277),
            'M5 coverage method check')
    require([i['sha256'] for i in m5['inputs'] if i['path'] == '.git'] == [M5_POINTER],
            'M5 worktree pointer method check')
    changed = git(repo, 'diff', '--name-only', M5_COMMIT, COMMIT).split()
    parser = sha(blob(repo, COMMIT, CHANGED))
    retained = {p: sha(blob(repo, COMMIT, p)) for p in RETAINED}
    require(all(sha(blob(repo, M5_COMMIT, p)) == d for p, d in retained.items()), 'retained pins moved')
    target = coverage(repo, COMMIT, AUTH)
    require((len(target['inputs']), len(target['trees']), len(target['links']), target['tracked']) == (12, 20, 2, 294),
            'target coverage shape')
    return dict(commit=COMMIT, tree=git(repo, 'rev-parse', COMMIT + '^{tree}').strip(), authority=AUTH,
                changed_paths=changed, parser_new=parser, retained_template_pins=retained,
                worker_version_new=deps_version(repo, COMMIT, parser, CLI), coverage=target)


if __name__ == '__main__':
    require(len(sys.argv) == 2, 'usage: derive_m6.py <repository>')
    print(json.dumps(derive(sys.argv[1]), indent=1, sort_keys=True))
