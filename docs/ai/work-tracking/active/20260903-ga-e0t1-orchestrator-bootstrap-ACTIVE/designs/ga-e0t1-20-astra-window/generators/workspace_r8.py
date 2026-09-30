"""Exact R7 startup additions; no widening of the ignored-file allowance."""
import json
from pathlib import Path

BASELINE=Path('/var/tmp/ga-e0t1.20-window-20260928-r7/workspace-before.json')
BASELINE_SHA='3d14a6a55068b89ecfccbea03b5c6c3bfc28839e576d0afa91d4a2ff90267104'
REPORT_SHA='03c8af6ecc7bf28e1af31319047647578bc52a01042a94fafb820cdb8110f074'
VALIDATOR_SHA='f6102dee7f7dd89f89236600aebe8035ebfe0ffde96aa5a4bda49221e4dac9a6'
PRIOR_FILES=('.gc/worker-evidence/ga-e0t1.20/positive-write.txt',
             '.gc/worker-evidence/ga-e0t1.20/startup.json',
             '.gc/worker-evidence/ga-e0t1.20/r7/positive-write.txt',
             '.gc/worker-evidence/ga-e0t1.20/r7/startup.json')


def verify(w,current,runtime):
    prior=w.module(w.HERE/'prior-startup-validation-r7.py',VALIDATOR_SHA)
    before=json.loads(w.read(BASELINE,BASELINE_SHA))
    prior.pristine_startup(before,current,REPORT_SHA,runtime)
    return before
