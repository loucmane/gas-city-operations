"""Terminal-only recovery of r4's preserved failed city-suspend observation.

The applied command's observation remains a FAILURE. No event is synthesized,
no lifecycle command retried and no state written by this verifier.
"""
import copy
import json
import os
from pathlib import Path

WINDOW = Path('/var/tmp/ga-e0t1.20-window-20260928-r4')
HOLD = Path('/var/tmp/ga-e0t1.20-r4-hold-20260928T105616Z')
CLOSE = Path('/var/tmp/ga-e0t1.20-r4-close-20260928T105721Z')
WATCH = Path('/var/tmp/ga-e0t1.20-r4-watch-20260928T105300Z')
RELEASE = Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r4')
PINS = {
    WINDOW/'suspension-baseline.json': 'fd131fbe1593b7c2aa43d0ab7a5b13a9b5c82bfe3ab7e047b7ed3319e78a5133',
    WINDOW/'suspension-rig-resume-intent.json': 'a92e5a5bbc403b2ec1e90490ab093cfb9708b783670466ad28b938bbe683c2e5',
    WINDOW/'suspension-rig-resume-event.json': '3ec761d56f87cdc90175935bdc932fd43e48177420980f3ac280a34313bd4946',
    WINDOW/'rig-resume-started.json': '8d6a9cd46d8e8e1143461cade24feb962e34ec8b9cfa8fbd3468746a51f73312',
    WINDOW/'rig-resume-phase.json': '92e755146e832aa08bc9284e8f0e340ad4429bb90ce31a8507060c88d2da99bc',
    WINDOW/'suspension-city-resume-intent.json': 'c998574d3e61de5f0b5676ba5d80e0e8ed8a61ae6562911248e5de8e6d5e2782',
    WINDOW/'suspension-city-resume-event.json': '8e5e20c9e8c5479071fecce4ac7ffccb798e471b36d908640da723c0cf089cd5',
    WINDOW/'city-resume-started.json': 'd6135ca4bc48ebe42c7e74e8f76df50402c4bb7d108a9556ae8e5b9c257ad192',
    WINDOW/'city-resume-phase.json': '03523df0cfec58c4cb0d42cead4065c0f0b10efc163814ff8a92f50f53cf473a',
    WINDOW/'suspension-city-suspend-intent.json': 'e4d6e663a16588657c4779e1575e183dc6453ee0a47c6d9bf8b18c0b8b4941e5',
    WINDOW/'suspension-city-suspend-failure.json': '18342cfcaac07953c663f0ccbc7267424de68580d67afe2ddd272aa7cbf952e4',
    WINDOW/'suspension-city-suspend-refused-after.json': 'f4dbe6e0d31a585cfd3d5868f47a47469389fb18950e24c2adf68c7350c868b2',
    WINDOW/'city-suspend-started.json': '80d332b222bf6db86d12aecba25acb4425016cf4ff9e2e5a33da45e539919ae4',
    WINDOW/'city-suspend-phase.json': '3dc2c588b53df27defd903ab7f34cc5608e804f88d9e5fa53c6111dd2698ee23',
    WINDOW/'city-suspend-status-0-phase.json': '00349ff8a0a808a619052734588f8f2f63b1fe4d864abfc3321ecd562e25e2f0',
    WINDOW/'city-suspend-sessions-0-phase.json': 'bbb41f274c3ccae3f14f865e3c076198f3b7a966dbf4c561a40011f441ce8c2c',
    HOLD/'attempts.json': '93c162d2f978ee1e9f67fbd685c0886361cef3848dd5b80cfd5fa5cd8316b4a5',
    HOLD/'intent.json': '9f60f3c60d77bdac9c607fbd59c9a86ea8b9aa108a51011a50a1c0c6d0594812',
    HOLD/'result.json': 'a6b3f700b134f91e5b3d74580201077c55b8516c5180a7ab43ddad2bbc26a2fc',
    HOLD/'rig-suspend-phase.json': '7c2b844587e765d50d4432c718e7b91aeb4b79f598a0fc28bcf94e05f888a1b1',
    HOLD/'rig-suspend-started.json': '3a5f917dd78062bde0bdb54cd8ec228f0e634676800928a905c338a5ad95203f',
    HOLD/'status-after-0-phase.json': 'f21978687548652ae1abfc72a6e7d6bbaec789fa5e322bd70ccfa8641c4c5e9d',
    CLOSE/'result.json': 'f750713fa030994846de51e3f5151b041a70454996134d41ad162a06126f57e8',
    WATCH/'result.json': 'd5520ae8d5f75b923a8b9c7a5f260f1c63225d4852f350a234ec96a752d70a12',
}
ENDPOINT_SHA = '8834ce8aec128720a78915830018581654aae241b6d2f995269d2df06f3120dd'
ENDPOINT_METADATA = dict(device=2096, inode=4292634, uid=1000, gid=1000,
    mode=0o644, type=0o100000, nlink=1, size=503,
    mtime_ns=1790592983654013462, ctime_ns=1790592983654013462)


def verify(w, s, current, *, terminal):
    w.require(terminal is True and w.ROOT == WINDOW, 'recovery admits only this terminal window')
    for suffix, actions in (
        ('intent', ['city-resume', 'city-suspend', 'rig-resume']),
        ('event', ['city-resume', 'rig-resume']),
        ('failure', ['city-suspend']), ('refused-after', ['city-suspend'])):
        w.require(sorted(p.name for p in WINDOW.glob('suspension-*-'+suffix+'.json'))
                  == ['suspension-'+a+'-'+suffix+'.json' for a in actions],
                  'unreviewed lifecycle '+suffix)
    w.require(not list(WINDOW.glob('rig-suspend-*')), 'unreviewed window rig suspension')
    w.require(not os.path.lexists(RELEASE), 'source release must remain unconsumed')
    records = {path: json.loads(w.read(path, pin)) for path, pin in PINS.items()}
    baseline = records[WINDOW/'suspension-baseline.json']
    events = []
    for action in ('rig-resume', 'city-resume'):
        event = records[WINDOW/('suspension-'+action+'-event.json')]
        w.require(event['action'] == action, 'wrong completed action')
        w.require(records[WINDOW/('suspension-'+action+'-intent.json')] ==
                  dict(action=action, before=event['before'],
                       before_sha256=event['before']['pin']['sha256']), 'completed intent binding')
        w.require(event['intent'] == records[WINDOW/(action+'-started.json')]
                  and event['result'] == records[WINDOW/(action+'-phase.json')],
                  'completed phase binding')
        events.append(event)
    intent = records[WINDOW/'suspension-city-suspend-intent.json']
    before = intent['before']
    w.require(intent == dict(action='city-suspend', before=before,
                            before_sha256=before['pin']['sha256']), 'suspend intent binding')
    s.chain(baseline, events, before, str(WINDOW), read_account=w.suspension_read_equal)
    s.phase(records[WINDOW/'city-suspend-started.json'], records[WINDOW/'city-suspend-phase.json'],
            'city-suspend', str(WINDOW))
    refused = records[WINDOW/'suspension-city-suspend-refused-after.json']
    s.step(before, refused, 'city-suspend', w.suspension_read_equal)
    w.require(records[WINDOW/'suspension-city-suspend-failure.json'] ==
              dict(error='active session count', automatic_replay=False), 'different refusal')
    census = json.loads(records[WINDOW/'city-suspend-sessions-0-phase.json']['stdout'])
    w.require(census['ok'] is True and census['sessions'] == []
              and census['summary']['active'] == 0, 'unexpected refusal census')
    watch = records[WATCH/'result.json']
    w.require(watch['ok'] is True and len(watch['live_sessions']) == 1
              and watch['live_sessions'][0]['id'] == 'ci-72ehy'
              and watch['live_sessions'][0]['work_dir'] ==
                  '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
              and watch['task']['status'] == 'open' and watch['task']['assignee'] is None,
              'unexpected pre-release worker history')
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
    w.require(records[CLOSE/'result.json'] == dict(ok=True, closed_session=None, open_sessions=0,
        city_tmux_sessions=0, worktree_processes=0, signals_sent=False, tmux_server_killed=True,
        executor_sha256='dbe568f3c63708a13c3b5c9336af2967148f952c06580c7b9850af1f8cde5f2b'),
        'close identity or residue proof')
    return current['pin']
