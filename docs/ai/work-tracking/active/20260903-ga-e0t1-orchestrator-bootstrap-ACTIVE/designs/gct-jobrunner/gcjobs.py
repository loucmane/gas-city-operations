#!/usr/bin/env python3
# gas-city-jobrunner status (installed as ~/.local/bin/gcjobs by operator/INSTALL.sh). Read-only.
"""One screen of Gas City job runner status: the service, its state, the queue and recent jobs.

Usage: gcjobs [-n LINES]   (LINES of runner.log to show, default 8)
It only reads the staging directory and asks systemd for the unit state; it never changes anything.
"""
import calendar
import json
import os
import subprocess
import sys
import time

STAGE = os.path.expanduser('~/.local/share/gas-city-staging/jobs')
UNIT = 'gas-city-jobrunner.service'


def local(iso):
    """'2026-09-23T15:03:02Z' -> '17:03:02' in the machine's local time zone; unparsable input unchanged."""
    try:
        return time.strftime('%H:%M:%S', time.localtime(calendar.timegm(time.strptime(iso, '%Y-%m-%dT%H:%M:%SZ'))))
    except (TypeError, ValueError):
        return str(iso)


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def unit_state():
    try:
        done = subprocess.run(['systemctl', '--user', 'show', '-p', 'ActiveState', '-p', 'SubState',
                               '-p', 'UnitFileState', UNIT], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        return {'error': str(exc)}
    return dict(line.split('=', 1) for line in done.stdout.splitlines() if '=' in line)


def recent_jobs(done_dir, limit=5):
    """Newest first: (job_id, started, ended, exit, package, note)."""
    try:
        entries = os.listdir(done_dir)
    except OSError:
        return []
    jobs = []
    for entry in entries:
        if entry.endswith('.started.json'):
            job_id = entry[:-len('.started.json')]
            started = read_json(os.path.join(done_dir, entry)) or {}
            final = read_json(os.path.join(done_dir, job_id + '.json'))
            wrapper = (started.get('job') or {}).get('wrapper', '')
            package = wrapper.split('/')[-3] if wrapper.count('/') >= 2 else wrapper
            if final is not None:
                note = 'finished'
            elif os.path.exists(os.path.join(done_dir, job_id + '.resolved.json')):
                note = 'resolved by coordinator'
            else:
                note = 'RUNNING or unfinished'
            jobs.append((started.get('started', ''), job_id, (final or {}).get('ended', ''),
                         (final or {}).get('exit', ''), package, note))
        elif '.refused-' in entry:
            record = read_json(os.path.join(done_dir, entry)) or {}
            jobs.append((record.get('received', ''), entry.split('.')[0], '', 'refused', '',
                         (record.get('refusal') or '')[:90]))
    jobs.sort(reverse=True)
    return jobs[:limit]


def tail(path, lines):
    try:
        with open(path, errors='replace') as handle:
            return handle.read().splitlines()[-lines:]
    except OSError:
        return []


def render(stage, unit, lines=8):
    out = []
    active = unit.get('ActiveState', unit.get('error', 'unknown'))
    out.append('Gas City job runner: service %s (%s, %s)' % (active, unit.get('SubState', '?'),
                                                              unit.get('UnitFileState', '?')))
    runner = read_json(os.path.join(stage, 'state', 'runner.json')) or {}
    if runner:
        out.append('  pid %s, up since %s, last poll %s, state: %s' % (
            runner.get('pid'), local(runner.get('started')), local(runner.get('last_poll')), runner.get('state')))
    if os.path.lexists(os.path.join(stage, 'PAUSE')):
        out.append('PAUSED by the operator (rm %s to resume)' % os.path.join(stage, 'PAUSE'))
    halted = read_json(os.path.join(stage, 'state', 'HALTED'))
    if halted:
        out.append('HALTED since %s: %s' % (local(halted.get('at')), halted.get('reason')))
        out.append('  (normal after every job: the coordinator records the outcome, then clears it)')
    try:
        queued = sorted(os.listdir(os.path.join(stage, 'queue')))
    except OSError:
        queued = []
    out.append('Queue: %s' % (', '.join(queued) if queued else '(empty)'))
    jobs = recent_jobs(os.path.join(stage, 'done'))
    out.append('Recent jobs (newest first):')
    if not jobs:
        out.append('  (none)')
    for started, job_id, ended, code, package, note in jobs:
        span = '%s-%s' % (local(started), local(ended)) if ended else local(started)
        out.append('  %-18s %-19s exit %-8s %-18s %s' % (job_id, span, code, package, note))
    log = tail(os.path.join(stage, 'runner.log'), lines)
    if log:
        out.append('Log (last %d lines of runner.log):' % len(log))
        out.extend('  ' + line for line in log)
    out.append('Pause: touch %s/PAUSE   Stop: systemctl --user stop gas-city-jobrunner' % stage)
    out.append('Follow: journalctl --user -u gas-city-jobrunner -f')
    return '\n'.join(out)


def main(argv):
    lines = 8
    if len(argv) == 3 and argv[1] == '-n' and argv[2].isdigit():
        lines = int(argv[2])
    elif len(argv) != 1:
        print(__doc__)
        return 2
    print(render(STAGE, unit_state(), lines))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
