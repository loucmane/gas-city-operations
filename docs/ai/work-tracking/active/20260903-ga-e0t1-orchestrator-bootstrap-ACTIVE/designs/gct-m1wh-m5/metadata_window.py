"""Fixed dual-clock metadata observation window, without wall-clock equality."""
import re
import time
from pathlib import Path

SECOND = 1_000_000_000
WINDOW = 900 * SECOND
MARGIN = 10 * SECOND
LIMIT = 2**63 - 1


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def integer(value):
    require(type(value) is int and 0 < value <= LIMIT, 'nonphysical timestamp')
    return value


def sample(value):
    require(set(value) == {'boot', 'mono', 'boot_time', 'wall', 'span'}, 'clock sample shape')
    require(isinstance(value['boot'], str) and re.fullmatch(
        r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value['boot']), 'boot identity')
    for key in ('mono', 'boot_time', 'wall'):
        integer(value[key])
    require(type(value['span']) is int and 0 <= value['span'] <= SECOND, 'clock span')
    return value


def clocks():
    before = time.monotonic_ns()
    boot_time = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    wall = time.time_ns()
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    after = time.monotonic_ns()
    return sample(dict(boot=boot, mono=after, boot_time=boot_time,
                       wall=wall, span=after-before))


def build(start, cache, attempt):
    sample(start)
    require(isinstance(attempt, str) and re.fullmatch(r'[0-9a-f]{64}', attempt), 'attempt identity')
    require(bool(cache['inventory']), 'empty cache')
    atimes = []
    for item in cache['inventory'].values():
        a, m, c = (integer(item[key]) for key in ('atime_ns', 'mtime_ns', 'ctime_ns'))
        require(max(m, c) < a <= start['wall'], 'unsettled or future cache timestamp')
        atimes.append(a)
    renewal = integer(min(atimes) + 86400 * SECOND)
    require(start['wall'] + WINDOW + MARGIN < renewal, 'cache renewal too near')
    return dict(attempt=attempt, start=dict(start), renewal=renewal, max_atime=max(atimes),
                mono_deadline=integer(start['mono']+WINDOW),
                boot_deadline=integer(start['boot_time']-start['span']+WINDOW))


def check(window, now, cache, attempt, finite=True):
    sample(now)
    # Reconstruct every deadline from the original sample and exact cache. Never renew.
    require(window == build(window['start'], cache, attempt), 'window binding changed')
    start = window['start']
    require(now['boot'] == start['boot'], 'boot changed')
    require(now['mono'] >= start['mono'] and now['boot_time'] >= start['boot_time'],
            'elapsed clock reversed')
    if finite:
        require(now['mono']+now['span'] < window['mono_deadline'], 'monotonic window expired')
        require(now['boot_time']+now['span'] < window['boot_deadline'], 'suspend-inclusive window expired')
        require(window['max_atime'] <= now['wall'], 'cache access time became future')
        require(now['wall']+MARGIN < window['renewal'], 'cache renewal horizon')


def admit(window, now, cache, attempt):
    """Reserve the complete native 65s transaction at the actual spawn boundary."""
    check(window, now, cache, attempt)
    reserve = 65*SECOND + SECOND  # full outer budget plus dispatch/sampling margin
    remaining = min(window['mono_deadline']-now['mono']-now['span'],
                    window['boot_deadline']-now['boot_time']-now['span'],
                    window['renewal']-MARGIN-now['wall']-now['span'])
    require(remaining > reserve, 'insufficient fixed window for full native lifetime')
