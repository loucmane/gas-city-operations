"""Exact preserved R9 startup additions and no product-source allowance."""
import json
from pathlib import Path

BASELINE=Path('/var/tmp/ga-e0t1.20-window-20260929-r9/workspace-before.json')
BASELINE_SHA='84308a2936fb703488ab4096741bb7027d5460c27124785f04f78f3ec874f4b6'
REPORT_SHA='acd31b3343f1d514c3f4f1ad23bbb5cd5f4c5d33cb14fd485d29cf8a1fbec726'
VALIDATOR_SHA='bee09009ca9ef83bb226b3fd89b4017267a214bc1e2a1ac3464a3788fba1f2b9'
PRIOR_FILES=('.gc/worker-evidence/ga-e0t1.20/positive-write.txt',
    '.gc/worker-evidence/ga-e0t1.20/startup.json',
    '.gc/worker-evidence/ga-e0t1.20/r7/positive-write.txt',
    '.gc/worker-evidence/ga-e0t1.20/r7/startup.json',
    '.gc/worker-evidence/ga-e0t1.20/r8/positive-write.txt',
    '.gc/worker-evidence/ga-e0t1.20/r8/startup.json',
    '.gc/worker-evidence/ga-e0t1.20/r9/positive-write.txt',
    '.gc/worker-evidence/ga-e0t1.20/r9/startup.json')


def verify(w,current,runtime):
    prior=w.module(w.HERE/'prior-startup-validation-r9.py',VALIDATOR_SHA)
    before=json.loads(w.read(BASELINE,BASELINE_SHA))
    prior.pristine_startup(before,current,REPORT_SHA,runtime)
    return before
