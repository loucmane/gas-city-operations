"""Read-only native resolution proof; writes only a fresh diagnostic evidence root."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

package = Path(sys.argv[1]); out = Path(sys.argv[2])
assert not out.exists()
out.mkdir(mode=0o700)
spec = importlib.util.spec_from_file_location('preparation', package/'prepare.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
old = m.configure(m.load())
data = m.inputs(old)
frozen = json.loads(data['config.baseline.json'])
declared = json.loads(data['window-r2-declared-delta.json'])
with (out/'city.window-r3.toml').open('xb') as stream:
    stream.write(data['city.window-r3.toml'])


def native(argv, overlay=False):
    command = ['/usr/bin/bwrap', '--ro-bind', '/', '/', '--unshare-net', '--new-session',
               '--die-with-parent', '--proc', '/proc', '--dev', '/dev']
    if overlay:
        command += ['--ro-bind', str(out/'city.window-r3.toml'), str(old.CITY/'city.toml')]
    p = subprocess.run([*command, '--', *argv], env=old.ENV, cwd='/',
                       stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
    assert p.returncode == 0, (p.returncode, p.stderr[-2000:])
    return json.loads(p.stdout)


def save(name, value):
    raw = (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()
    with (out/name).open('xb') as stream:
        stream.write(raw)
    return hashlib.sha256(raw).hexdigest()


baseline = native([str(old.GC), '--city', str(old.CITY), 'config', 'show', '--json'])
save('config.before.json', baseline)
assert baseline == frozen, 'baseline drift'
actual = native([str(old.GC), '--city', str(old.CITY), 'config', 'show', '--json'], True)
save('config.r3.json', actual)
expected = m.expected_config(frozen, declared)
save('config.expected.json', expected)
assert expected == actual, 'native configuration differs from the declared exact delta'
before = native([str(old.COMPOSE)])
after = native([str(old.COMPOSE)], True)
save('composition.before.json', before); save('composition.r3.json', after)
assert before['permission_revision'] == old.REVISION and after['permission_revision'] != old.REVISION
assert {k:v for k,v in before.items() if k != 'permission_revision'} == {
    k:v for k,v in after.items() if k != 'permission_revision'}
assert native([str(old.GC), '--city', str(old.CITY), 'config', 'show', '--json']) == baseline
result = dict(ok=True, installed=False, worker_launched=False, source_repair=False,
              revision_after=after['permission_revision'], exact_agent_inventory=114,
              only_target='gascity/codex', live_configuration_unchanged=True,
              resume_same_single_worktree=True, mcp_disabled_in_configuration=True)
save('result.json', result)
print(json.dumps(result, sort_keys=True))
