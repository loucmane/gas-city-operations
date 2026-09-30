"""Read-only exact-source proof, not apply and not live recovery acceptance."""
from pathlib import Path
import hashlib
import json
import types

PATH = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window/generators/helper_recovery.py')
SHA = '0b2458d691d93a1672757314a34f9e8c1efbc97f87df42adee18b4be28aec90a'
ROOT = Path('/tmp/ga-e0t1-r7-recovery/host-proof-final')
raw = PATH.read_bytes()
assert hashlib.sha256(raw).hexdigest() == SHA
m = types.ModuleType('recovery_proof')
m.__file__ = str(PATH)
m._SOURCE_SHA = SHA
exec(compile(raw, str(PATH), 'exec', dont_inherit=True), m.__dict__)
m.ARCHIVE = ROOT
ROOT.mkdir(mode=0o700)
m.verify_sandbox_binary()
w, load = m.load_package()
b, o, owned = w.load_support()
host = m.confined_host_observation(w, o, owned, 'proof')
load('runtime-process-r7.py').verify_assets(load('worker-startup-r7.py').read_regular)
workspace = m.child(w, owned, 'inner-before')
m.save(ROOT, 'result.json', dict(ok=True, actual_host=host, workspace=workspace,
       executor_sha256=SHA, live_mutation=False, full_apply=False))
print(json.dumps(dict(ok=True, root=str(ROOT), host_verified=True,
      all_gc_diagnostics_confined=True, live_mutation=False, full_apply=False)))
