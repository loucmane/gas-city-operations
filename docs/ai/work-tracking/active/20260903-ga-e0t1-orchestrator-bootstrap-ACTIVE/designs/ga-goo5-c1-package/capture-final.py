"""Read-only fresh ga-goo5 baseline capture. Fresh evidence only; no worker or live write."""
import hashlib
import json
from pathlib import Path
import types

ROOT = Path('/tmp/ga-goo5-readonly-baseline-20260930-r2')
D = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window')
PRIOR = Path('/var/tmp/ga-5uc9-terminal-20260930-r1/observed-after.json')
PRIOR_SHA = '8402af1f87cf131ed08e7d754bae82a993240e04dffd2f42edddf07bdfbab5dc'


def module(path, pin):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pin
    value = types.ModuleType(path.stem)
    value.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), value.__dict__)
    return value


def save(name, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with (ROOT/name).open('xb') as stream:
        stream.write(raw)
    return hashlib.sha256(raw).hexdigest()


def delta(a, z, path=()):
    if type(a) != type(z):
        return [dict(path=list(path), before=a, after=z)]
    if isinstance(a, dict):
        out = []
        for key in sorted(set(a) | set(z)):
            if key not in a or key not in z:
                out.append(dict(path=list(path+(key,)), before=a.get(key), after=z.get(key)))
            else:
                out += delta(a[key], z[key], path+(key,))
        return out
    return [] if a == z else [dict(path=list(path), before=a, after=z)]


assert not ROOT.exists()
ROOT.mkdir(mode=0o700)
w = module(D/'window-base-r11.py', '746e3dcdea4412380dc8d7e5f1b622f4637ad05d26605e19bbedee6e71e000d0')
b, o, owned = w.load_support()
prior = json.loads(w.read(PRIOR, PRIOR_SHA))
h = w.host(o)
observed = dict(host=h, pins={path: o.read_file(path)[0] for path in prior['pins']},
                cache=o.tree_snapshot(b.CACHE, cache=True),
                protected={str(p): o.tree_snapshot(p, protected=True) for p in b.PROTECTED})
assert h == w.host(o), 'host changed'
observed_sha = save('observed.json', observed)
changes = delta(w.dependency_image({k: prior[k] for k in w.ACCEPTED_KEYS}),
                w.dependency_image(observed))
provider = w.provider_pins(b, o)
provider_changes = delta(w.dependency_image(json.loads(w.read(w.PROVIDER, w.PROVIDER_SHA))),
                         w.dependency_image(provider))
save('providers.json', provider)
N = Path("/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-goo5-c1-package")
v = module(N/'startup-validation.py', '6af3b62f4dd1deea841687f1f93025423da5caf367762437919b5ffb954dbbf9')
i = module(D/'candidate-inspect.py', '3a204f4adf9bbd4f1b3723e8941a0266c3ea69bc711cb36e80c79cf1340a3e53')
workspace = v.workspace_image(Path(v.WORK), i.file_bytes)
assert workspace == v.workspace_image(Path(v.WORK), i.file_bytes), 'workspace not stable'
workspace_sha = save('workspace.json', workspace)
strict = module(N/'fresh-workspace.py', '5b2dde047fcf7123ef3304ea057f20ca79d26222a360ee617e5415aaf43f0812')
c = module(N/'contract.py', '8869a5b205129a95308c798aade10043957b611f54c6c20f73589670c2797f21')
strict.verify(types.SimpleNamespace(contract=lambda: c, require=w.require), workspace, c.RUNTIME_IMAGE)
entry = observed['cache']['inventory'][w.CACHE_DIRECTORY]
allowed_paths = {('cache', 'inventory', w.CACHE_DIRECTORY, key) for key in ('mtime_ns', 'ctime_ns')}
allowed = (all(tuple(row['path']) in allowed_paths for row in changes)
           and entry['mtime_ns'] == entry['ctime_ns']
           and entry['mtime_ns'] >= prior['cache']['inventory'][w.CACHE_DIRECTORY]['mtime_ns']
           and not provider_changes)
result = dict(observed_sha256=observed_sha, accepted_predecessor_sha256=PRIOR_SHA,
              non_atime_deltas=changes, provider_deltas=provider_changes,
              workspace_entries=len(workspace), workspace_sha256=workspace_sha,
              allowed_difference_set=allowed, cache_pin_ns=entry['mtime_ns'],
              worker_launched=False, execution_admitted=False)
save('result.json', result)
print(json.dumps(result, sort_keys=True))
assert allowed, 'unexpected baseline drift'
