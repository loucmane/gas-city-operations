"""Offline proof of the prep checks that only a live job would otherwise reach. Read-only.

Answers the r2 review HOLD with the committed prep-r11.py code (its digest must equal PREP.sh's PREP_SHA),
with ROOT redirected to a fresh scratch directory:
1. The confined `gc order list --json` against the pinned r1 overlay bytes (5f3b60e1) reports no
   orders, in exactly the shape main() asserts; `gc config show` equals the r1 observation and
   expected_config().
2. receipt_image() runs the exact job child path: normalize through the source launcher
   (`python3 -I -S -B`), then Core `compose finalize`, each in bwrap --unshare-pid --new-session
   under the Core owned-phase runner:
   - with the live revision d6ca85cd, the final receipt is byte-identical to the live receipt 0b30c23f;
   - with the r1 overlay revision 6b31d83a, it differs from the live receipt only in
     permission_revision and receipt_sha256, which is main()'s difference check.
Every child runs under bwrap --ro-bind / /, so nothing outside the scratch directory is written.
gc runs with GIT_OPTIONAL_LOCKS=0 (prep ENV).

Usage: python3 -B prep-proof.py <fresh scratch directory>   (prints and writes report.json there)
"""
import hashlib
import json
import re
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PREP = HERE/'prep-r11.py'
R1 = Path('/var/tmp/ga-4z38-prep-20260923-r1')
OVERLAY_REVISION = '6b31d83ab039cd1cba61ac77845fe71f4d6ce8b06f8a775f07df1e42d6bfd6ba'


def load():
    [pin] = re.findall(r'^PREP_SHA=([0-9a-f]{64})$', (HERE/'operator'/'PREP.sh').read_text(), re.M)
    raw = PREP.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pin, 'prep-r11.py differs from the PREP.sh pin'
    p = types.ModuleType('prep_r11')
    p.__file__ = str(PREP)
    exec(compile(raw, str(PREP), 'exec', dont_inherit=True), p.__dict__)
    return p, pin


def main(scratch):
    p, pin = load()
    scratch = Path(scratch)
    scratch.mkdir(mode=0o700)
    p.ROOT = scratch
    city = p.read(p.CITY/'city.toml', p.CITY_SHA)
    live_receipt = p.read(p.RECEIPT, p.RECEIPT_SHA)
    prior = p.read(p.PRIOR, p.PRIOR_SHA)
    composition = json.loads(p.read(R1/'composition.after.json'))
    assert composition['permission_revision'] == OVERLAY_REVISION
    report = dict(prep_sha256=pin)
    # 1. Orders and effective config under the pinned overlay bytes.
    r1_city = p.read(R1/'city.baseline.toml', p.CITY_SHA)
    candidate, _, names, target, selected = p.build_overlay(
        r1_city, json.loads(p.read(R1/'config.baseline.json')), json.loads(p.read(R1/'orders.baseline.json')))
    assert p.sha(candidate) == p.OVERLAY_SHA
    p.write('city.isolated.toml', p.read(R1/'city.isolated.toml', p.OVERLAY_SHA))
    empty = p.confined([str(p.GC), '--city', str(p.CITY), 'order', 'list', '--json'], True)
    p.write('orders.isolated.json', empty)
    report['orders_isolated'] = dict(orders=empty['orders'], summary=empty['summary'],
                                     main_check_passes=empty['orders'] == [] and empty['summary']['count'] == 0)
    observed = p.config(True)
    report['config_isolated'] = dict(
        equals_r1_observation=observed == json.loads(p.read(R1/'config.isolated.json')),
        equals_expected_config=observed == p.expected_config(
            json.loads(p.read(R1/'config.baseline.json')), selected, target, names))
    # 2. The receipt image, through the exact job child path, for both revisions.
    owned = p.module(p.BUILD/'phase_runner.py', p.RUNNER_PHASE_SHA, 'owned_phase')
    p.read(p.BUILD/'compose', p.FINALIZE_SHA)
    p.read(p.LAUNCH, p.LAUNCH_SHA)
    old = json.loads(live_receipt)
    for revision in (p.REVISION, OVERLAY_REVISION):
        sub = scratch/revision[:8]
        sub.mkdir(mode=0o700)
        candidate_input = json.loads(prior)
        candidate_input['permission_revision'] = revision
        p.write('receipt.input.json', candidate_input, sub)
        final = p.receipt_image(owned, PREP, pin, sub)
        new = json.loads(final)
        report[revision[:8]] = dict(
            final_sha256=p.sha(final), bytes_equal_live=final == live_receipt,
            differences=sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k)),
            permission_revision=new['permission_revision'], receipt_self_sha256=new['receipt_sha256'])
    report['live_unchanged'] = p.read(p.CITY/'city.toml') == city and p.read(p.RECEIPT) == live_receipt
    report['ok'] = (report['orders_isolated']['main_check_passes']
                    and all(report['config_isolated'].values())
                    and report[p.REVISION[:8]]['bytes_equal_live']
                    and report[OVERLAY_REVISION[:8]]['differences'] == ['permission_revision', 'receipt_sha256']
                    and report['live_unchanged'])
    p.write('report.json', report)
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
