"""Exact R10 startup additions preserved; no product-source allowance."""
import json
from pathlib import Path
BASELINE=Path('/var/tmp/ga-e0t1.20-window-20260929-r10/workspace-before.json')
BASELINE_SHA='d0d2333b69bcc6851560edec42fd180b5dc88d288968c7deaa81248106754d9a'
REPORT_SHA='e8e6fa2832cbf10fee1d24ffae3a753047d87838d38d00c7745f36efece4849d'
VALIDATOR_SHA='b6380f86b3205e95471e38a9303034fb5a11b96f9690d5b86c184953a4639595'
PRIOR_FILES=('.gc/worker-evidence/ga-e0t1.20/positive-write.txt',
    '.gc/worker-evidence/ga-e0t1.20/startup.json',
    '.gc/worker-evidence/ga-e0t1.20/r7/positive-write.txt','.gc/worker-evidence/ga-e0t1.20/r7/startup.json',
    '.gc/worker-evidence/ga-e0t1.20/r8/positive-write.txt','.gc/worker-evidence/ga-e0t1.20/r8/startup.json',
    '.gc/worker-evidence/ga-e0t1.20/r9/positive-write.txt','.gc/worker-evidence/ga-e0t1.20/r9/startup.json',
    '.gc/worker-evidence/ga-e0t1.20/r10/positive-write.txt','.gc/worker-evidence/ga-e0t1.20/r10/startup.json')
def verify(w,current,runtime):
    prior=w.module(w.HERE/'prior-startup-validation-r10.py',VALIDATOR_SHA)
    before=json.loads(w.read(BASELINE,BASELINE_SHA))
    prior.pristine_startup(before,current,REPORT_SHA,runtime)
    return before
