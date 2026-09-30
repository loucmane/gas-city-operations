"""Exact preserved R8 startup additions and no product-source allowance."""
import json
from pathlib import Path

BASELINE = Path('/var/tmp/ga-e0t1.20-window-20260928-r8/workspace-before.json')
BASELINE_SHA = '55367521030cf18055b653dd66ad9e5c2b4a54f8ad0d0d975a7cfe1719c33951'
REPORT_SHA = 'eea89174ed3b2ec78bc01253c674e12049c044ffc10967a961dbb4b66431079b'
VALIDATOR_SHA = '3c2ad7f7322b0560a74698d557ae016ab874a1ce02dfdc87ad2f1a3fc1eb2dd2'
PRIOR_FILES = ('.gc/worker-evidence/ga-e0t1.20/positive-write.txt',
    '.gc/worker-evidence/ga-e0t1.20/startup.json',
    '.gc/worker-evidence/ga-e0t1.20/r7/positive-write.txt',
    '.gc/worker-evidence/ga-e0t1.20/r7/startup.json',
    '.gc/worker-evidence/ga-e0t1.20/r8/positive-write.txt',
    '.gc/worker-evidence/ga-e0t1.20/r8/startup.json')


def verify(w, current, runtime):
    prior = w.module(w.HERE/'prior-startup-validation-r8.py', VALIDATOR_SHA)
    before = json.loads(w.read(BASELINE, BASELINE_SHA))
    prior.pristine_startup(before, current, REPORT_SHA, runtime)
    return before
