"""Exact preserved R6 startup additions, not a generic ignored-file exception."""
import json
from pathlib import Path

BASELINE=Path('/var/tmp/ga-e0t1.20-window-20260928-r6/workspace-before.json')
BASELINE_SHA='5c750ffdfcfdbcbf87ce80048aa39bd7aa4ec1591fabf1f5854cc66e6810a83d'
REPORT_SHA='0ef1635eed2de2b4160ca333c3f3dd411b13c0a7aca72a90ebfd2f8e4bb7455c'
VALIDATOR_SHA='2c7fcef75391ae0507c085428c117088131d1f1695884d5ef0200f1df115630a'
PRIOR_FILES=('.gc/worker-evidence/ga-e0t1.20/positive-write.txt',
             '.gc/worker-evidence/ga-e0t1.20/startup.json')


def verify(w,current,runtime):
    prior=w.module(w.HERE/'prior-startup-validation-r6.py',VALIDATOR_SHA)
    before=json.loads(w.read(BASELINE,BASELINE_SHA))
    prior.pristine_startup(before,current,REPORT_SHA,runtime)
    return before
