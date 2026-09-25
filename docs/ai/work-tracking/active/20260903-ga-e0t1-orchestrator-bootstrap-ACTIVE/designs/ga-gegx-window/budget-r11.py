"""Refuse when the window's four-hour cache-atime bound leaves too little time for the next step.

Every snapshot after PREFLIGHT is bounded by cache-atime-policy-r1.py bounds(): the boot-clock time from
the window before.json clock start to the newest sample must stay within MAX_WINDOW_NS (four hours).
RESTORE consumes itself before its first bound check, and replaces city.toml before its reload's
check, so a restore started too late can fail half-way. ADMIT.sh, RESTORE.sh and TERMINAL.sh run this
gate first, with the minutes each still needs. Read-only: it reads the window before.json and the
kernel clocks, and writes nothing.

Usage (through the source launcher): budget-r11.py <required minutes>
"""
import json
import os
from pathlib import Path
import stat
import sys
import time

WINDOW = Path('/var/tmp/ga-gegx-window-20260925-r2')
MAX_WINDOW_NS = 4 * 3600 * 10**9  # cache-atime-policy-r1.py MAX_WINDOW_NS


def read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    try:
        s = os.fstat(fd)
        if not (stat.S_ISREG(s.st_mode) and s.st_uid == 1000):
            raise RuntimeError('before.json authority')
        raw = b''
        while chunk := os.read(fd, 1 << 20):
            raw += chunk
    finally:
        os.close(fd)
    return raw


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdigit() or not 1 <= int(sys.argv[1]) <= 120:
        raise RuntimeError('usage: budget-r11.py <required minutes 1..120>')
    required = int(sys.argv[1])
    start = json.loads(read(WINDOW/'before.json'))['cache_access_clock']['start']
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if boot != start['boot']:
        raise RuntimeError('boot changed since before.json')
    now = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    left = MAX_WINDOW_NS - (now - start['boot_before_ns'])
    report = dict(minutes_left=round(left / 6e10, 1), minutes_required=required, enough=left >= required * 6 * 10**10)
    print(json.dumps(report))
    return 0 if report['enough'] else 1


if __name__ == '__main__':
    sys.exit(main())
