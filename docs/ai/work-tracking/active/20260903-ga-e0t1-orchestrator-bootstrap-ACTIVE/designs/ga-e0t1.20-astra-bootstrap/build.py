"""Create-only assembly of the two pre-window jobs. Never executes either job."""
import hashlib
import base64
import json
from pathlib import Path
import sys

O = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap')
T = O/'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE'
P = T/'reports/gct-oak5-astra-operations-bootstrap-20260927'
S = T/'designs/gct-e8ex-window'
NAME = 'ga-e0t1.20-astra-bootstrap'
WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
MCP_ARGS = ['-c', 'mcp_servers.serena.enabled=false', '-c', 'mcp_servers.aegis.enabled=false']
RESUME = ("/home/loucmane/gascity/bin/codex resume --model gpt-6-astra -c model_reasoning_effort=high "
          "--ask-for-approval never --sandbox workspace-write -c "
          "'sandbox_workspace_write.writable_roots=[\"" + WORK + "\"]' "
          "-c mcp_servers.serena.enabled=false -c mcp_servers.aegis.enabled=false {{.SessionKey}}")
INPUTS = {
    'city.window-r2.toml': 'dfa4d979a27c9b8d5fe8a21c5bfbb9bb425fdc6e5848647454dd02d3d9d8cdae',
    'window-r2-declared-delta.json': '4bea8b42e4b85f9444f0097304c16c588618ca587aa83424cd7b0c8784dfdcc6',
    'config.baseline.json': '2440317ed9832d69e7bfd4766f65eda54e9337b7f36626ca6cc8fee34fbb47ca',
    'orders.baseline.json': '96d2952125d9ff3b5d986f77929c581691b604d58fec62f95cc1edcf6fb607b3',
    'window-restrictions.rules': 'ea2645785163d3f9b6d5ddfe8a08c5ff40b97a8cb1739bca94dd4b2844f15773',
}


def render(destination):
    assert not destination.exists(), 'assembly destination consumed'
    files = {}
    for name, digest in INPUTS.items():
        raw = (P/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest, name
        files['inputs/'+name] = raw
    # R3 is append-forward. R2 remains preserved and never becomes a runnable window.
    # Resume must not inherit the whole candidate-root grant from the parent provider.
    # The source checkout's two MCP servers are unnecessary for the three-file task.
    old = b'[providers.codex-managed]\nbase = "provider:codex"\n'
    new = old + ('args_append = '+json.dumps(MCP_ARGS)+'\nresume_command = '+json.dumps(RESUME)+'\n').encode()
    assert files['inputs/city.window-r2.toml'].count(old) == 1
    files['inputs/city.window-r3.toml'] = files['inputs/city.window-r2.toml'].replace(old, new)
    # Preserve exact original evidence bytes, including intentional trailing
    # newlines, in an explicit lossless container rather than changing them to
    # satisfy text whitespace checks or weakening those checks.
    archive = {name.removeprefix('inputs/'): base64.b64encode(raw).decode('ascii')
               for name, raw in files.items()}
    files = {'inputs.json': (json.dumps(archive, sort_keys=True, indent=2)+'\n').encode()}
    for name in ('prepare.py', 'worktree.py', 'test_package.py', 'README.md', 'build.py', 'check_native.py'):
        files[name] = (Path(__file__).parent/name).read_bytes()
    # The PREP wrapper is the reviewed S5 wrapper with identity and source binding only.
    raw = (S/'operator/PREP.sh').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == 'ce00810e590531617317f9623c7ae88f32d7d533170172188bf5fc46b27b5a1d'
    template = raw.decode()
    template = template.replace('gct-e8ex-window', NAME).replace('gct-mbg6', 'ga-e0t1.20')
    template = template.replace('prep-20260926-r1', 'prep-20260927-r1')
    template = template.replace('prep-r11.py', 'prepare.py')
    template = template.replace('6cd7c219338c46607f1fbf53a5aad6e92383062f35e76c546e1aab997ea07322',
                                hashlib.sha256(files['prepare.py']).hexdigest())
    # Replace historical commentary, not executable statements.
    first = template.index('S=/home/')
    template = '#!/bin/sh\n# S1 PREP: read-only host observation and uninstalled image. No worker launch.\n' + template[first:]
    template = template.replace('git -c core.fsmonitor', 'git --no-optional-locks -c core.fsmonitor')
    files['operator/PREP.sh'] = template.encode()
    raw = (S/'operator/WORKTREE.sh').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == 'c5d7d93c77334badea6a4da227e55e83c51dca77baf9b9a31c529fd6442e6622'
    template = raw.decode().replace('gct-e8ex-window', NAME).replace('gct-mbg6', 'ga-e0t1.20')
    template = template.replace('worktree-20260926-r1', 'worktree-20260927-r1')
    template = template.replace('worktree-task-r1.py', 'worktree.py')
    template = template.replace('310f75d0d1e29e99a8305a03caa4245e81dd445045986b60eca50bc8bb0108aa',
                                hashlib.sha256(files['worktree.py']).hexdigest())
    first = template.index('S=/home/')
    template = '#!/bin/sh\n# S1 WORKTREE: create only the exact unsigned Operations workspace and local rules.\n' + template[first:]
    template = template.replace('git -c core.fsmonitor', 'git --no-optional-locks -c core.fsmonitor')
    files['operator/WORKTREE.sh'] = template.encode()
    manifest = {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(files.items())}
    destination.mkdir(mode=0o700)
    for name, raw in files.items():
        path = destination/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    with (destination/'assembly.json').open('x') as stream:
        json.dump(dict(schema='ga-e0t1.20.s1-assembly.v1', files=manifest,
                       live_execution=False, source_base='c6b789bbe6ff677dd04336803dbf2c2e017812ba'),
                  stream, indent=2, sort_keys=True)
        stream.write('\n')
    return manifest


if __name__ == '__main__':
    print(json.dumps(render(Path(sys.argv[1])), indent=2, sort_keys=True))
