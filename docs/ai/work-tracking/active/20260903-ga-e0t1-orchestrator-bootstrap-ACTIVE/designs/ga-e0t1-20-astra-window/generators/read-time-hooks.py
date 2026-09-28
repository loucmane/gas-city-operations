"""Source-included operational adapters for the exact four-object exception."""


def read_time_policy():
    return module(HERE/'read-time-accounting.py', 'ASSEMBLY_READ_TIME_SHA')


def read_time_bounds(baseline_clock=None):
    policy = module(HERE/'cache-atime-policy-r1.py',
        '61c3e38e4475061c658a853036922742ab2ce69d44a4577e3f91490674047783')
    def sample():
        first = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        real = time.time_ns()
        last = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        return dict(boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            real_ns=real, boot_before_ns=first, boot_after_ns=last)
    if baseline_clock is None:
        baseline_clock = record('before.json')['cache_access_clock']
    return policy.bounds(baseline_clock,
                         dict(start=sample(), end=sample()))


def read_time_evidence(kind, before, after, changes, window):
    if not changes:
        return
    require(kind in ('suspension', 'directories', 'routes'), 'read-time evidence kind')
    value = dict(schema='ga-e0t1.20.four-object-read-times.v1', kind=kind,
        before=before, after=after, changes=changes, window=window,
        timestamp_writes=False, worker_authority_changed=False)
    pin = digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())
    name = 'read-times-'+kind+'-'+pin+'.json'
    if os.path.lexists(ROOT/name):
        require(record(name) == value, 'read-time accounting collision')
    else:
        save(name, value)


def suspension_read_equal(before, after):
    window = read_time_bounds()
    aligned, changes = read_time_policy().suspension(before, after, window)
    require(before == aligned, 'unrecorded suspension mutation')
    read_time_evidence('suspension', before, after, changes, window)
    return True


def suspension_pin_equal(before, after):
    window = read_time_bounds()
    require(set(before) == set(after) == {'sha256', 'metadata'}
        and before['sha256'] == after['sha256'], 'suspension pin content changed')
    aligned, changes = read_time_policy().metadata(str(SUSPENSION),
        before['metadata'], after['metadata'], window)
    require(before['metadata'] == aligned, 'suspension pin metadata changed')
    read_time_evidence('suspension', before, after, changes, window)
    return True


def route_read_account(before, after, window, *, regenerated=False):
    # Only the city .beads parent participates. Route-file metadata, content,
    # other rigs and native regeneration proofs remain the caller's exact checks.
    require(str(CITY) in before and str(CITY) in after, 'city route mirror absent')
    aligned, changes = read_time_policy().metadata(str(CITY/'.beads'),
        before[str(CITY)]['parent'], after[str(CITY)]['parent'], window,
        renamed=regenerated)
    result = json.loads(json.dumps(after))
    result[str(CITY)]['parent'] = aligned
    read_time_evidence('routes', before, after, changes, window)
    return result
