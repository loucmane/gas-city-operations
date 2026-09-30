"""Read-only terminal disposition of the exact September 28 resume refusal.

No event is synthesized, no failure removed, and no lifecycle retry authorized.
The original failed command observation remains failed. Only terminal recovery
may validate its applied command plus the distinct reviewed safety HOLD.
"""
import copy
import json
from pathlib import Path

WINDOW = Path('/var/tmp/ga-9olv-window-20260929-r1')
HOLD = Path('/var/tmp/ga-9olv-r3-hold-20260928T083013Z')
CLOSE = Path('/var/tmp/ga-9olv-r3-close-20260928T083154Z')
PINS = {
    WINDOW/'suspension-baseline.json': 'fc780bb9ed0b93bf580c27e973b98494c79f834fb75072bd0b06c4c822c89d81',
    WINDOW/'suspension-rig-resume-intent.json': '2df4c0749fce4c7a106a57343aff95aedf39f96302e65f7957bc2bfd00d9793e',
    WINDOW/'suspension-rig-resume-failure.json': '18342cfcaac07953c663f0ccbc7267424de68580d67afe2ddd272aa7cbf952e4',
    WINDOW/'suspension-rig-resume-refused-after.json': '960d246186bcf25e787afd4c58607683d5be45f2af8d9303d591e07df7e9e701',
    WINDOW/'rig-resume-started.json': '6aed8014f1430c4f68e5b8381cdfa0a5c24613a686611808fb2d0d3612510d47',
    WINDOW/'rig-resume-phase.json': '34511445eec2c12de844d9c7bb1846b01d416743e10b085c7abf684e90c985f3',
    WINDOW/'rig-resume-sessions-0-phase.json': '9790fd84b806440314e1533f2a398b413037e5c51e0077a11068a2a820c7c754',
    HOLD/'attempts.json': '93c162d2f978ee1e9f67fbd685c0886361cef3848dd5b80cfd5fa5cd8316b4a5',
    HOLD/'intent.json': '43e4d70f123b370184285fb3565ac7bddd01ed83cbe2521b30668951a1c414d7',
    HOLD/'result.json': 'ef684e4f58c90e4437bd6724f975adecb8ed709d45af745b7dbac08dfcce503b',
    HOLD/'rig-suspend-phase.json': 'a5c39dde76f937e50a4d9d139771b480e19d9245b1315ae36983300a2b9707da',
    HOLD/'rig-suspend-started.json': '41e80a95d85726e09148c52a15acb85cc21bc12b20c0b54869816e299b8d9a25',
    HOLD/'status-after-0-phase.json': '7f3ca2110be2bd905772a0bdbd0ba27e127a7fbef89e2a5b0ceef4e8e3517fe1',
    CLOSE/'result.json': '0888b33dfb7d8111f2ebbfe414d5eb3956acdacb1e56ab2c8dbf97032fb71bd8',
}
ENDPOINT_SHA = 'c6628a825fb938eb00c470bdccb8adecde0edf4df158823fb9df8c4eb7f5d44b'
ENDPOINT_METADATA = dict(device=2096, inode=4877394, uid=1000, gid=1000,
    mode=0o644, type=0o100000, nlink=1, size=502,
    mtime_ns=1790584220575668043, ctime_ns=1790584220575668043)


def verify(w, s, current, *, terminal):
    w.require(terminal is True and w.ROOT == WINDOW,
              'recovery admits only this terminal window')
    w.require(sorted(p.name for p in WINDOW.glob('suspension-*-intent.json'))
              == ['suspension-rig-resume-intent.json'], 'unreviewed lifecycle intent')
    w.require(not list(WINDOW.glob('suspension-*-event.json')), 'unexpected lifecycle event')
    for suffix in ('failure', 'refused-after'):
        w.require(sorted(p.name for p in WINDOW.glob('suspension-*-'+suffix+'.json'))
                  == ['suspension-rig-resume-'+suffix+'.json'], 'unreviewed lifecycle refusal')
    for prefix in ('city-resume', 'city-suspend', 'rig-suspend'):
        w.require(not list(WINDOW.glob(prefix+'-*')), 'unexpected window lifecycle operation')
    records = {path: json.loads(w.read(path, pin)) for path, pin in PINS.items()}
    baseline = records[WINDOW/'suspension-baseline.json']
    intent = records[WINDOW/'suspension-rig-resume-intent.json']
    before = intent['before']
    w.require(intent == dict(action='rig-resume', before=before,
                            before_sha256=before['pin']['sha256']), 'resume intent binding')
    s.chain(baseline, [], before, str(WINDOW), read_account=w.suspension_read_equal)
    s.phase(records[WINDOW/'rig-resume-started.json'], records[WINDOW/'rig-resume-phase.json'],
            'rig-resume', str(WINDOW))
    refused = records[WINDOW/'suspension-rig-resume-refused-after.json']
    s.step(before, refused, 'rig-resume', w.suspension_read_equal)
    w.require(records[WINDOW/'suspension-rig-resume-failure.json'] ==
              dict(error='active session count', automatic_replay=False), 'different refusal')
    census = json.loads(records[WINDOW/'rig-resume-sessions-0-phase.json']['stdout'])
    w.require(census['ok'] is True and census['sessions'] == []
              and census['summary']['active'] == 0, 'worker existed at refusal')
    hold = records[HOLD/'result.json']
    w.require(hold['ok'] is True and hold['city_suspended'] is True
              and hold['gascity_rig_suspended'] is True and hold['window_root_written'] is False
              and hold['city_suspended_before'] is True and hold['rig_suspended_before'] is False
              and hold['epoch_before'] == 'verified', 'hold result')
    w.require(records[HOLD/'attempts.json'] == {'rig-suspend': 0}, 'hold operations')
    s.phase(records[HOLD/'rig-suspend-started.json'], records[HOLD/'rig-suspend-phase.json'],
            'rig-suspend', str(HOLD))
    w.require(current['pin']['sha256'] == ENDPOINT_SHA, 'terminal suspension bytes drift')
    metadata = dict(current['pin']['metadata'])
    metadata.pop('atime_ns')
    w.require(metadata == ENDPOINT_METADATA, 'terminal suspension identity drift')
    s.step(refused, current, 'rig-suspend', w.suspension_read_equal)
    z = s.image(current)
    expected = copy.deepcopy(s.image(baseline))
    expected['updated_at'] = z['updated_at']
    w.require(z == expected, 'suspension baseline not restored')
    closed = records[CLOSE/'result.json']
    w.require(closed == dict(ok=True, closed_session=None, open_sessions=0,
        city_tmux_sessions=0, worktree_processes=0, signals_sent=False,
        tmux_server_killed=False,
        executor_sha256='fab5bf6d06a261b326de253b52f39bbf12dad0d0c059b6c4e4fb3ff0a9396f58'),
        'close identity or residue proof')
    return current['pin']
