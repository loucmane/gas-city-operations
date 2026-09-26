"""Bounded successor orchestration, composed with exact frozen helper sources.

No entry point runs on import. Assemble first; the isolated pinned launcher then
invokes the inherited closed stage grammar. No broker submission or Core install.
"""
import hashlib
import os
from pathlib import Path
import secrets
import subprocess
import time
import types

LOCAL_SOURCES = ('source_runtime.py', 'manifest_candidate.py', 'metadata_window.py',
                 'metadata_closure.py', 'metadata_executor.py', 'launch.py')
PROBE_LIMIT = 36.0


def assemble(runtime, candidate, window_policy, closure_module):
    graph = runtime.legacy()
    o, b, a, s, n, f, c = (graph[name] for name in (
        'observe_recovery', 'build_manifest', 'prepare_short_artifacts', 'recovery_state',
        'recovery_native', 'recovery_final', 'recovery_controller'))
    accepted = closure_module.configure(graph, candidate)
    n.PROBE_LIMIT = PROBE_LIMIT
    original_package = c.package
    original_native = n.native

    def sources():
        pins = {}
        for name, expected in runtime.PINS.items():
            path = runtime.LEGACY / (name + '.py')
            pins[str(path)] = runtime.source(path, expected)[1]
        for name in LOCAL_SOURCES:
            path = runtime.HERE / name
            pins[str(path)] = runtime.source(path)[1]
        return pins

    def receipt(host):
        value = candidate.receipt()
        candidate.r7.validate_receipt_epoch(value, host)
        o.require(host == accepted['host'], 'accepted complete service epoch changed')

    def package(expected):
        p, manifest = original_package(expected)
        old = o.read_file(candidate.OLD_ROOT + '/q/manifest.json', collect=True)[1]
        baseline = o.read_file(candidate.BASELINE_PATH, collect=True)[1]
        rebuilt, report = candidate.build(old, baseline, accepted['host'],
            manifest['metadata']['parents'], manifest['metadata']['transaction'], manifest['metadata']['attempt'])
        o.require(rebuilt == manifest and report == p['report'], 'pure manifest reconstruction drift')
        return p, manifest

    def prepare():
        o.require(not os.path.lexists(s.ROOT), 'fresh metadata package root already consumed')
        source_pins = sources()
        old = o.read_file(candidate.OLD_ROOT + '/q/manifest.json', collect=True)[1]
        baseline = o.read_file(candidate.BASELINE_PATH, collect=True)[1]
        host = o.host_observation()
        receipt(host)
        timer = c.timer_state()
        c.timer_idle(timer, True)
        original = o.decode(old)
        platform_parent = s.parent(original['metadata']['parents'][0]['path'])
        o.require(platform_parent == original['metadata']['parents'][0], 'platform parent changed')
        # Only isolated append-forward package directories are created here. A
        # failure after this point consumes r9; no automatic replay or cleanup.
        a.exclusive_directory(s.ROOT, 0o700)
        for name in ('b', 't', 'q'):
            a.exclusive_directory(s.ROOT / name, 0o700)
        s.record('prepare-consumed.json', dict(sources=source_pins, host=host, timer=timer,
                                             metadata_mutation=False))
        parents = [platform_parent, s.parent(s.ROOT/'b'), s.parent(s.ROOT/'t')]
        manifest, report = candidate.build(old, baseline, host, parents,
                                           secrets.token_hex(32), secrets.token_hex(32))
        s.preimages(manifest)
        s.record('manifest.json', manifest)
        started = window_policy.clocks()
        deadline = window_policy.build(started, accepted['cache'], manifest['metadata']['attempt'])
        s.record('preparation-pause-intent.json', dict(sources=source_pins, before_timer=timer,
                 manifest_file_sha256=s.digest(s.RECORDS/'manifest.json'), deadline=deadline,
                 accepted_recovery_sha256=candidate.BASELINE_SHA))
        window_policy.check(deadline, window_policy.clocks(), accepted['cache'], manifest['metadata']['attempt'])
        stopped = subprocess.run(['/usr/bin/systemctl', '--user', 'stop', o.TIMER], env=o.ENV,
                                 cwd='/', stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        s.record('preparation-pause-command.json', dict(returncode=stopped.returncode,
                 stdout=stopped.stdout.decode(errors='replace'), stderr=stopped.stderr.decode(errors='replace')))
        o.require(stopped.returncode == 0, 'preparation timer stop failed; no replay')
        paused = wait_idle(False)
        closure = s.snapshot(manifest)
        o.require(c.timer_state() == paused, 'preparation paused state drift')
        window_policy.check(deadline, window_policy.clocks(), closure['cache'], manifest['metadata']['attempt'])
        o.require(sources() == source_pins, 'preparation source drift')
        s.record('preparation-closure.json', closure)
        s.record('preparation-paused.json', dict(paused_timer=paused, deadline=deadline,
                 intent_sha256=s.digest(s.RECORDS/'preparation-pause-intent.json'),
                 command_sha256=s.digest(s.RECORDS/'preparation-pause-command.json'),
                 closure_sha256=s.digest(s.RECORDS/'preparation-closure.json')))
        result = dict(schema='gc.metadata-successor-package.v1', preparation_only=True,
                      live_acceptance=False, sources=source_pins, timer=timer, report=report,
                      timer_paused=True, native_launched=False,
                      preparation_paused_sha256=s.digest(s.RECORDS/'preparation-paused.json'),
                      manifest_file_sha256=s.digest(s.RECORDS/'manifest.json'),
                      closure_sha256=s.digest(s.RECORDS/'preparation-closure.json'),
                      accepted_recovery_sha256=candidate.BASELINE_SHA,
                      broker_receipt_sha256=candidate.RECEIPT_SHA,
                      timing=dict(warm_probe_seconds=PROBE_LIMIT, grant_seconds=60,
                                  lease_seconds=63, outer_seconds=65,
                                  no_external_process_timeout=True))
        s.record('prepared.json', result)
        return result

    def wait_idle(active):
        deadline = time.monotonic_ns() + 30_000_000_000
        wanted = dict(ActiveState='active' if active else 'inactive',
                      SubState='waiting' if active else 'dead',UnitFileState='enabled',Result='success')
        while True:
            value = c.timer_state()
            service = value['reconciler']
            if service['MainPID'] == '0' and value['timer'] == wanted:
                c.timer_idle(value, active)
                return value
            # Natural drain only, never signal/start/reset the reconciler.
            allowed_timer = (wanted, dict(wanted,SubState='running')) if active else (wanted,)
            o.require(value['timer'] in allowed_timer and service['NRestarts'] == '0'
                      and service['UnitFileState'] == 'static'
                      and service['ActiveState'] in ('activating','active','deactivating','inactive','failed'),
                      'unexpected reconciler instability')
            o.require(time.monotonic_ns() < deadline, 'reconciler failed to drain naturally')
            time.sleep(0.25)

    def pause(expected, p, manifest):
        c.source_review(expected, p)
        for name in ('pause-consumed.json', 'pause-command.json', 'window.json',
                     'restore-consumed.json', 'restore-command.json', 'restored.json'):
            o.require(not os.path.lexists(s.RECORDS/name), 'window consumed')
        s.preimages(manifest)
        staged = s.read(s.RECORDS/'preparation-paused.json', p['preparation_paused_sha256'])
        intent = s.read(s.RECORDS/'preparation-pause-intent.json', staged['intent_sha256'])
        stopped = s.read(s.RECORDS/'preparation-pause-command.json', staged['command_sha256'])
        o.require(stopped['returncode'] == 0 and intent['sources'] == p['sources'] == sources()
                  and intent['manifest_file_sha256'] == p['manifest_file_sha256']
                  and staged['closure_sha256'] == p['closure_sha256']
                  and intent['before_timer'] == p['timer']
                  and intent['deadline'] == staged['deadline']
                  and intent['accepted_recovery_sha256'] == candidate.BASELINE_SHA
                  and p['timer_paused'] is True and p['native_launched'] is False,
                  'prepaused preparation lineage')
        timer = intent['before_timer'];deadline = intent['deadline']
        c.timer_idle(timer, True)
        o.require(c.timer_state() == staged['paused_timer'], 'prepared pause epoch drift')
        window_policy.check(deadline, window_policy.clocks(), accepted['cache'], manifest['metadata']['attempt'])
        before = s.snapshot(manifest)
        receipt(before['host'])
        o.require(before == s.read(s.RECORDS/'preparation-closure.json', p['closure_sha256']),
                  'preparation preservation drift')
        s.record('pause-consumed.json', dict(package_sha256=expected, before_timer=timer,
                                           closure=before, deadline=deadline))
        after = wait_idle(False)
        first = s.snapshot(manifest)
        o.require(first == before, 'pause preservation drift')
        time.sleep(5)
        second = s.snapshot(manifest)
        o.require(second == first and c.timer_state() == after, 'second quiet observation drift')
        s.preimages(manifest)
        window_policy.check(deadline, window_policy.clocks(), second['cache'], manifest['metadata']['attempt'])
        value = dict(package_sha256=expected, before_timer=timer, paused_timer=after, closure=second,
                     deadline=deadline, pause_sha256=s.digest(s.RECORDS/'pause-consumed.json'))
        s.record('window.json', value)
        return dict(ok=True, window_sha256=s.digest(s.RECORDS/'window.json'))

    def current(manifest, expected, finite=True):
        value = c.baseline()
        pause_record = s.read(s.RECORDS/'pause-consumed.json', value['pause_sha256'])
        o.require(value['package_sha256'] == pause_record['package_sha256'] == expected
                  and value['before_timer'] == pause_record['before_timer']
                  and value['closure'] == pause_record['closure']
                  and value['deadline'] == pause_record['deadline'], 'window/pause lineage')
        if finite:
            o.require(all(not os.path.lexists(s.RECORDS/name)
                          for name in ('restore-consumed.json', 'restored.json')), 'window permanently closed')
        def clock_check():
            window_policy.check(value['deadline'], window_policy.clocks(), value['closure']['cache'],
                                manifest['metadata']['attempt'], finite=finite)
        clock_check()
        o.require(c.timer_state() == value['paused_timer'], 'paused service epoch drift')
        observed = s.snapshot(manifest)
        receipt(observed['host'])
        o.require(observed == value['closure'], 'complete preservation drift')
        clock_check()
        return value

    def equivalent(result, reviewed, warm=False):
        o.require(n.clean(result) and result['stdout'] == reviewed['stdout']
                  and result['stderr'] == reviewed['stderr'], 'native plan/process differs')
        o.require(type(result['elapsed_ns']) is int and result['elapsed_ns'] >= 0, 'native elapsed domain')
        if warm:
            o.require(result['elapsed_ns'] <= int(PROBE_LIMIT*1e9), 'warm probe exceeds 36 seconds; no third try')

    def native(phase, baseline_sha):
        # Exact executable is bound by current() immediately before dispatch and
        # by every native validation. No shell, timeout wrapper, API credential or
        # inherited environment enters this standalone CLI invocation. Cobra's
        # Execute path supplies Background; native code starts its own 65s budget.
        o.require(o.GC_SHA == candidate.NEW and o.ENV == expected_env, 'native invocation profile drift')
        value = s.read(s.RECORDS/'window.json', baseline_sha)
        manifest = s.read(s.RECORDS/'manifest.json')
        def spawn(*args, **kwargs):
            # Called by the unchanged native helper AFTER its consumed record is
            # durable and immediately before Popen. Record latency cannot steal
            # the reserved native lifetime unnoticed. No retry on refusal.
            window_policy.admit(value['deadline'], window_policy.clocks(), value['closure']['cache'],
                                manifest['metadata']['attempt'])
            return subprocess.Popen(*args, **kwargs)
        prior_subprocess = n.subprocess
        n.subprocess = types.SimpleNamespace(Popen=spawn, DEVNULL=subprocess.DEVNULL,
                                             PIPE=subprocess.PIPE)
        try:
            return original_native(phase, baseline_sha)
        finally:
            n.subprocess = prior_subprocess

    def restore(expected, p, manifest, accepted_result):
        o.require(all(not os.path.lexists(s.RECORDS/name) for name in
                      ('restore-consumed.json', 'restore-command.json', 'restored.json')),
                  'restore consumed')
        value = current(manifest, expected, finite=False)
        if accepted_result:
            acceptance = s.read(s.RECORDS/'committed-acceptance.json')
            o.require(acceptance['package_sha256'] == expected and acceptance['ok'] is True, 'acceptance binding')
            c.review('COMMIT_PASS', dict(package_sha256=expected,
                                       acceptance_sha256=s.digest(s.RECORDS/'committed-acceptance.json')))
            fresh = f.outputs(manifest)
            o.require(all(acceptance.get(k) == v for k, v in fresh.items()), 'committed pair drift')
            commit = s.read(s.RECORDS/'commit-result.json')
            o.require(n.clean(commit) and s.digest(s.RECORDS/'commit-result.json') ==
                      acceptance['commit_result_sha256'], 'commit terminal evidence drift')
        else:
            o.require(not os.path.lexists(s.RECORDS/'commit-consumed.json') and
                      not os.path.lexists(s.RECORDS/'commit-result.json'), 'apply may have launched')
            for phase in ('observe', 'probe', 'probe2'):
                consumed, result = (s.RECORDS/(phase+suffix) for suffix in ('-consumed.json', '-result.json'))
                o.require(os.path.lexists(consumed) == os.path.lexists(result), 'incomplete child evidence')
                if os.path.lexists(consumed):
                    row = s.read(result)
                    o.require(n.terminal(row) and row['phase'] == phase and row['baseline_sha256'] ==
                              s.digest(s.RECORDS/'window.json'), 'unproven terminal child')
            s.preimages(manifest)
        s.record('restore-consumed.json', dict(package_sha256=expected, accepted=accepted_result,
                                             before=c.timer_state(), expected_timer=value['before_timer']['timer']))
        result = subprocess.run(['/usr/bin/systemctl', '--user', 'start', o.TIMER], env=o.ENV,
                                cwd='/', stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        s.record('restore-command.json', dict(returncode=result.returncode,
                 stdout=result.stdout.decode(errors='replace'), stderr=result.stderr.decode(errors='replace')))
        o.require(result.returncode == 0, 'timer restoration failed')
        after = wait_idle(True)
        o.require(after['timer'] == value['before_timer']['timer'], 'timer semantic restoration differs')
        o.require(s.snapshot(manifest) == value['closure'], 'post-restoration preservation drift')
        if accepted_result:
            o.require(f.outputs(manifest) == fresh, 'post-restoration committed pair drift')
        else:
            s.preimages(manifest)
        s.record('restored.json', dict(ok=True, accepted=accepted_result, after=after,
                                      historical_reconciler_epoch_not_reset=True))
        return dict(ok=True, timer_restored=True, accepted=accepted_result)

    def recover_preparation(intent_sha):
        """Explicit restoration of an exactly proven preparation-only pause."""
        forbidden = ('pause-consumed.json', 'window.json', 'restore-consumed.json',
                     'restore-command.json', 'restored.json') + tuple(
            phase+suffix for phase in ('observe','probe','probe2','commit')
            for suffix in ('-consumed.json','-result.json'))
        o.require(all(not os.path.lexists(s.RECORDS/name) for name in forbidden),
                  'preparation recovery cannot cover native/window/restoration activity')
        intent = s.read(s.RECORDS/'preparation-pause-intent.json', intent_sha)
        o.require(intent['sources'] == sources()
                  and intent['accepted_recovery_sha256'] == candidate.BASELINE_SHA,
                  'preparation recovery source/baseline drift')
        manifest = s.read(s.RECORDS/'manifest.json', intent['manifest_file_sha256'])
        original = o.read_file(candidate.OLD_ROOT+'/q/manifest.json', collect=True)[1]
        baseline = o.read_file(candidate.BASELINE_PATH, collect=True)[1]
        rebuilt, _ = candidate.build(original, baseline, accepted['host'], manifest['metadata']['parents'],
                                     manifest['metadata']['transaction'], manifest['metadata']['attempt'])
        o.require(rebuilt == manifest, 'preparation recovery manifest reconstruction drift')
        stopped = s.read(s.RECORDS/'preparation-pause-command.json')
        o.require(stopped['returncode'] == 0, 'stop did not complete; ambiguous preparation')
        c.timer_idle(intent['before_timer'], True)
        before = wait_idle(False)
        s.preimages(manifest)
        observed = s.snapshot(manifest)
        receipt(observed['host'])
        window_policy.check(intent['deadline'], window_policy.clocks(), observed['cache'],
                            manifest['metadata']['attempt'], finite=False)
        s.record('restore-consumed.json', dict(recovery='preparation-before-native',
                 intent_sha256=intent_sha, before=before, closure=observed))
        result = subprocess.run(['/usr/bin/systemctl','--user','start',o.TIMER], env=o.ENV,
                                cwd='/', stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        s.record('restore-command.json', dict(returncode=result.returncode,
                 stdout=result.stdout.decode(errors='replace'), stderr=result.stderr.decode(errors='replace')))
        o.require(result.returncode == 0, 'preparation recovery restoration failed')
        after = wait_idle(True)
        o.require(after['timer'] == intent['before_timer']['timer'], 'original timer semantics drift')
        o.require(s.snapshot(manifest) == observed, 'preparation recovery preservation drift')
        s.preimages(manifest)
        s.record('restored.json', dict(ok=True, accepted=False, recovery='preparation-before-native',
                 after=after, intent_sha256=intent_sha, historical_reconciler_epoch_not_reset=True))
        return dict(ok=True, timer_restored=True, accepted=False, preparation_recovery=True)

    def recover_pause(expected, p, manifest):
        """Restore only a proven pre-native interrupted timer-pause stage.

        This is an explicit recovery command, never an automatic exception path.
        A window that completed must use the ordinary preapply restoration gate.
        """
        c.source_review(expected, p)
        forbidden = ('window.json', 'restore-consumed.json', 'restore-command.json', 'restored.json') + tuple(
            phase+suffix for phase in ('observe', 'probe', 'probe2', 'commit')
            for suffix in ('-consumed.json', '-result.json'))
        o.require(all(not os.path.lexists(s.RECORDS/name) for name in forbidden),
                  'interrupted-pause recovery cannot cover window/native/restore activity')
        pause_record = s.read(s.RECORDS/'pause-consumed.json')
        prepared = s.read(s.RECORDS/'preparation-closure.json', p['closure_sha256'])
        o.require(pause_record['package_sha256'] == expected and pause_record['closure'] == prepared,
                  'interrupted pause package/closure lineage')
        c.timer_idle(pause_record['before_timer'], True)
        window_policy.check(pause_record['deadline'], window_policy.clocks(), prepared['cache'],
                            manifest['metadata']['attempt'], finite=False)
        s.preimages(manifest)
        o.require(s.snapshot(manifest) == prepared, 'interrupted pause preservation drift')
        state = c.timer_state()
        o.require(state['timer']['ActiveState'] in ('active', 'inactive'), 'timer state ambiguous')
        active = state['timer']['ActiveState'] == 'active'
        before = wait_idle(active)
        receipt(prepared['host'])
        s.record('restore-consumed.json', dict(package_sha256=expected, accepted=False,
                 recovery='interrupted-pause-before-native', before=before,
                 pause_sha256=s.digest(s.RECORDS/'pause-consumed.json')))
        if not active:
            result = subprocess.run(['/usr/bin/systemctl', '--user', 'start', o.TIMER], env=o.ENV,
                                    cwd='/', stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
            s.record('restore-command.json', dict(returncode=result.returncode,
                     stdout=result.stdout.decode(errors='replace'), stderr=result.stderr.decode(errors='replace')))
            o.require(result.returncode == 0, 'interrupted pause timer restoration failed')
        after = wait_idle(True)
        o.require(after['timer'] == pause_record['before_timer']['timer'], 'timer semantics not restored')
        o.require(s.snapshot(manifest) == prepared, 'interrupted pause recovery preservation drift')
        s.preimages(manifest)
        s.record('restored.json', dict(ok=True, accepted=False, after=after,
                 recovery='interrupted-pause-before-native', timer_already_active=active))
        return dict(ok=True, timer_restored=True, accepted=False, pre_native_recovery=True)

    expected_env = dict(o.ENV)
    c.sources, c.package, c.prepare = sources, package, prepare
    c.pause, c.current = pause, current
    n.equivalent, n.native = equivalent, native
    # Keep original closed CLI grammar and its accepted keyword unchanged.
    c.restore = lambda expected, p, manifest, accepted: restore(expected, p, manifest, accepted)
    c.successor_wait_idle = wait_idle
    c.successor_receipt = receipt
    c.recover_pause = recover_pause
    c.recover_preparation = recover_preparation
    return graph
