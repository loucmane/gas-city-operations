"""Offline release barrier proofs. No city, process, worker or service mutation."""
import copy
import json
from pathlib import Path

import pytest
import release_delivery_r11 as d

S = dict(id='ci-example', session_name='codex-ci-example', continuation_epoch='1')
M = 'SOURCE RELEASE: ga-e0t1.20 session=ci-example report_sha256=' + 'a' * 64
BEFORE = b'{"type":"event_msg","payload":{"type":"task_complete"}}\n'
EXE = '/home/loucmane/gascity/bin/gc'
SHA = 'b' * 64
CG = '0::/user.slice/user-1000.slice/user@1000.service/app.slice/gc-job-test-release.service\n'
START = 1790642685.2
NUDGE = 'nudge-0123456789ab'
OLD = dict(id='nudge-02f0f513467f', session_id='ci-9dp7z', message='SOURCE RELEASE: preserved')
BASELINE = dict(pending=[OLD], dead=[dict(id='nudge-111111111111')])


def ingress(message=M):
    return json.dumps(dict(type='response_item', payload=dict(type='message', role='user',
        content=[dict(type='input_text', text=d.native_payload(message))]))).encode() + b'\n'


def snapshot(delivered=False, received=False):
    metadata = dict(message=M, session_id=S['id'], agent='gascity/codex', source='session',
                    nudge_id=NUDGE, state='injected' if delivered else 'queued',
                    commit_boundary='provider-nudge-return' if delivered else '',
                    terminal_reason='', last_error='', continuation_epoch='1')
    row = dict(id='ci-nudge', issue_type='chore', labels=['gc:nudge'], status='closed' if delivered else 'open',
               created_at='2026-09-29T00:44:45Z', metadata=metadata)
    queue = copy.deepcopy(BASELINE)
    if not delivered:
        queue['pending'].append(dict(id=NUDGE, bead_id='ci-nudge', session_id=S['id'], message=M,
            continuation_epoch='1', source='session', agent='gascity/codex'))
    poller = dict(alive=True, pid=123, start_ticks=456, uid=1000,
                  executable_sha256=SHA, cgroup=CG,
                  argv=[EXE, 'nudge', 'poll', '--city', '/home/loucmane/gascity/city',
                        '--session', S['session_name'], S['id']])
    return dict(receipts=[row], queue=queue, poller=poller,
                transcript=BEFORE + (ingress() if received else b''))


class Clock:
    value = 0

    def now(self): return self.value

    def sleep(self, seconds): self.value += seconds


def run(snapshots, timeout=3):
    clock = Clock()
    calls = []

    def observe(remaining):
        calls.append(remaining)
        return snapshots[min(len(calls) - 1, len(snapshots) - 1)]

    return d.wait(observe, clock.now, clock.sleep, S, M, BEFORE, START, BASELINE,
                  EXE, SHA, CG, timeout), calls


def test_native_enqueue_has_no_nudge_id_and_is_not_delivery():
    value = dict(schema_version='1', ok=True, target='gascity/codex', session_id=S['id'],
                 session_name=S['session_name'], delivery='queue', queued=True, outcome='queued')
    d.enqueue_result(value, S)
    assert 'nudge_id' not in value
    with pytest.raises(RuntimeError, match='timeout'):
        run([snapshot()])


def test_preserved_r10_response_proves_only_enqueue():
    root = Path('/var/tmp/ga-e0t1.20-startup-release-20260929-r10')
    phase = json.loads((root/'source-release-phase.json').read_bytes())
    result = json.loads((root/'result.json').read_bytes())
    watch = json.loads(Path('/var/tmp/ga-e0t1.20-r10-watch-20260929T004637Z/nudge.json').read_bytes())
    assert phase['exit_code'] == 0 and phase['stdout'] == 'Queued nudge for gascity/codex\n'
    assert result['source_release_sent'] is True and watch['queued'] == 1
    assert watch['pending'][0]['id'] == 'nudge-02f0f513467f'
    # The new executing wait cannot turn that class of enqueue-only state into PASS.
    with pytest.raises(RuntimeError, match='timeout'):
        run([snapshot()])


def test_delayed_ack_and_native_ingress_are_both_required():
    result, calls = run([snapshot(), snapshot(True), snapshot(True, True)])
    assert result['delivered'] and result['receipt']['nudge_id'] == NUDGE and len(calls) == 3


@pytest.mark.parametrize('delivered,received', [(False, False), (True, False), (False, True)])
def test_one_missing_half_never_passes(delivered, received):
    with pytest.raises(RuntimeError, match='timeout'):
        run([snapshot(delivered, received)])


@pytest.mark.parametrize('field,value', [('session_id','ci-other'), ('message','SOURCE RELEASE: wrong'),
    ('source','operator'), ('agent','other'), ('nudge_id','nudge-fake'),
    ('state','failed'), ('terminal_reason','expired'), ('last_error','transport failure'),
    ('commit_boundary','coordinator-drain')])
def test_receipt_negatives(field, value):
    snap = snapshot(True, True)
    snap['receipts'][0]['metadata'][field] = value
    with pytest.raises(RuntimeError): run([snap])


@pytest.mark.parametrize('field,value', [('issue_type','task'), ('status','open'),
    ('created_at','2026-09-28T00:00:00Z'), ('created_at','2026-09-29T00:44:45'),
    ('created_at','bad')])
def test_receipt_authority_and_time_negatives(field, value):
    snap = snapshot(True, True); snap['receipts'][0][field] = value
    with pytest.raises(RuntimeError): run([snap])


@pytest.mark.parametrize('labels', [[], None, 'gc:nudge', ['gc:message']])
def test_native_shadow_label_is_required(labels):
    snap = snapshot(True, True); snap['receipts'][0]['labels'] = labels
    with pytest.raises(RuntimeError): run([snap])


def test_status_output_is_not_the_readonly_queue_contract():
    snap = snapshot(True, True); snap['queue']['counts'] = dict(pending=1)
    with pytest.raises(RuntimeError): run([snap])


def test_absence_before_duplicate_and_disappearance_are_not_success():
    snap = snapshot(True, True)
    d.absence_before([], S, M)
    with pytest.raises(RuntimeError, match='already exists'): d.absence_before(snap['receipts'], S, M)
    snap['receipts'] *= 2
    with pytest.raises(RuntimeError, match='duplicate'): run([snap])
    snap['receipts'] = []
    with pytest.raises(RuntimeError, match='timeout'): run([snap])


def test_receipt_then_queue_removal_race_waits():
    snap = snapshot(True, True)
    snap['queue'] = snapshot()['queue']
    result, calls = run([snap, snapshot(True, True)])
    assert result['delivered'] and len(calls) == 2


@pytest.mark.parametrize('kind', ['pending','in_flight','dead'])
def test_foreign_or_failed_queue_item_refuses(kind):
    snap = snapshot(True, True)
    snap['queue'][kind] = [dict(id=NUDGE, session_id=S['id'], message='foreign')]
    with pytest.raises(RuntimeError): run([snap])


@pytest.mark.parametrize('field,value', [('alive',False), ('pid',True), ('uid',0),
    ('start_ticks',0), ('executable_sha256','c'*64), ('cgroup','0::/foreign.service\n'),
    ('argv',[EXE,'nudge','poll','ci-other'])])
def test_poller_must_be_the_live_owned_native_helper(field, value):
    snap = snapshot(True, True); snap['poller'][field] = value
    with pytest.raises(RuntimeError): run([snap])


def test_poller_replacement_refuses_even_with_completed_ack():
    done = snapshot(True, True); done['poller']['start_ticks'] += 1
    with pytest.raises(RuntimeError, match='identity changed'): run([snapshot(), done])


@pytest.mark.parametrize('suffix', [ingress()+ingress(), ingress('SOURCE RELEASE: foreign'),
    b'{invalid}\n', b'[]\n', json.dumps(dict(type='response_item', payload=dict(type='message',
      role='user', content=[dict(type='input_text',text='unrelated prompt')]))).encode()+b'\n'])
def test_native_transcript_negatives(suffix):
    snap = snapshot(True, True); snap['transcript'] = BEFORE + suffix
    with pytest.raises(RuntimeError): run([snap])


def test_prefix_partial_write_and_accounting():
    assert not d.transcript_ingress(BEFORE, BEFORE+b'{"partial":', M)
    accounting = b'{"type":"token_usage_record","payload":{}}\n'
    assert d.transcript_ingress(BEFORE, BEFORE+ingress()+accounting, M)
    with pytest.raises(RuntimeError, match='prefix'):
        d.transcript_ingress(BEFORE, b'changed\n'+ingress(), M)


@pytest.mark.parametrize('timeout', [0,-1,91,True,float('inf'),float('nan')])
def test_wait_is_bounded(timeout):
    with pytest.raises(RuntimeError): run([snapshot(True, True)], timeout)


def test_callback_cannot_report_success_after_deadline():
    clock = Clock()
    def slow(remaining):
        clock.value += remaining + 1
        return snapshot(True, True)
    with pytest.raises(RuntimeError, match='timeout'):
        d.wait(slow,clock.now,clock.sleep,S,M,BEFORE,START,BASELINE,EXE,SHA,CG,3)


def test_closed_session_nudge_is_preserved_not_mistaken_for_delivery():
    result, _ = run([snapshot(True, True)])
    assert result['receipt']['nudge_id'] != OLD['id']
    with pytest.raises(RuntimeError, match='timeout'):
        run([snapshot()])


@pytest.mark.parametrize('change', ['drop', 'edit', 'move', 'additional'])
def test_historical_queue_noninterference(change):
    snap = snapshot(True, True)
    if change == 'drop': snap['queue']['pending'] = []
    if change == 'edit': snap['queue']['pending'][0]['message'] += ' altered'
    if change == 'move': snap['queue']['dead'].extend(snap['queue'].pop('pending'))
    if change == 'additional': snap['queue']['pending'].append(dict(id='nudge-222222222222'))
    with pytest.raises(RuntimeError): run([snap])


@pytest.mark.parametrize('fence', ['', None, 'ci-example'])
def test_baseline_cannot_have_a_nudge_deliverable_to_the_new_worker(fence):
    baseline = copy.deepcopy(BASELINE); baseline['pending'][0]['session_id'] = fence
    with pytest.raises(RuntimeError): d.queue_baseline(baseline, S)


@pytest.mark.parametrize('field,value', [('session_id','ci-other'), ('source','operator'),
    ('continuation_epoch','2'), ('agent','other'), ('bead_id','other')])
def test_exact_new_queue_fence(field, value):
    snap = snapshot(); snap['queue']['pending'][-1][field] = value
    with pytest.raises(RuntimeError): run([snap])


def test_queue_duplicate_and_receipt_epoch_refuse():
    snap = snapshot(); snap['queue']['in_flight'] = [copy.deepcopy(snap['queue']['pending'][-1])]
    with pytest.raises(RuntimeError): run([snap])
    snap = snapshot(True, True); snap['receipts'][0]['metadata']['continuation_epoch'] = '2'
    with pytest.raises(RuntimeError): run([snap])
