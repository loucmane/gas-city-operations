"""Offline adapter/control-flow fixtures; never production acceptance."""
import hashlib
import copy
import json
from pathlib import Path
import types

import pytest
from test_queue_preservation import fixture, add_owned, SESSION, config, p

HERE=Path(__file__).parent


def load(name):
    m=types.ModuleType(name);m.__file__=str(HERE/name)
    exec(compile((HERE/name).read_bytes(),m.__file__,'exec'),m.__dict__)
    return m


def rig(tmp_path, monkeypatch):
    g=load('queue-guard.py')
    window=tmp_path/'window';window.mkdir()
    prep=tmp_path/'prep';prep.mkdir()
    (window/'before.json').write_text('{}\n')
    c=config();orders=dict(orders=[dict(name='nudge-on-route')])
    for suffix in ('baseline','isolated'):
        (prep/('config.'+suffix+'.json')).write_text(json.dumps(c))
        (prep/('orders.'+suffix+'.json')).write_text(json.dumps(orders))
    q,beads=fixture()
    state=dict(queue=q,beads=beads,session=None,failures=[],calls=[])
    monkeypatch.setattr(g,'WINDOW',window)
    monkeypatch.setattr(g,'read_queue',lambda w:json.dumps(state['queue']).encode())
    monkeypatch.setattr(g,'pollers',lambda w,s:[])
    def phase(label,args,b,owned,timeout):
        state['calls'].append((label,args))
        args=args[3:]
        if args[:2]==['session','list']:
            rows=[] if state['session'] is None else [dict(SESSION,template='gascity/codex',
                  rig='gascity',provider='codex-managed',work_dir=str(tmp_path/'candidate'))]
            value=dict(ok=True,sessions=rows)
        elif args[:2]==['bd','show']:
            value=[dict(id=SESSION['id'],issue_type='session',labels=['gc:session'],
                  metadata=dict(session_name=SESSION['session_name'],continuation_epoch=state['session'],
                                template='gascity/codex',provider='codex-managed',
                                **{'gc.trigger_bead_id':'ga-mb91','gc.trigger_bead_store_ref':'rig:gascity'}))]
        elif args[:2]==['bd','list']:value=state['beads']
        elif args[:2]==['config','show']:value=c
        elif args[:2]==['order','list']:value=orders
        else:raise AssertionError(args)
        return dict(stdout=json.dumps(value))
    def durable(path,raw):
        with path.open('xb') as f:f.write(raw)
    w=types.SimpleNamespace(ROOT=window,HERE=HERE,PREP=prep,WORK=tmp_path/'candidate',
        GC=['/fake/gc','--city','/fake/city'],require=p.require,phase=phase,
        read=lambda path:Path(path).read_bytes(),b_gc_sha=lambda:'a'*64,
        module=lambda path,pin:p,durable=durable)
    w.save=lambda name,value:durable(w.ROOT/name,(json.dumps(value,sort_keys=True)+'\n').encode())
    return g,w,state


def test_capture_then_owned_delivery_and_terminal_reuse_same_fixed_baseline(tmp_path,monkeypatch):
    g,w,s=rig(tmp_path,monkeypatch)
    assert g.checkpoint(w,'preflight',None,None,None,capture=True,scoped=False)['ok']
    before=(g.WINDOW/'foreign-before.json').read_bytes()
    s['session']='2';add_owned(s['queue'],s['beads'])
    assert g.checkpoint(w,'release-before',None,None,None)['ok']
    output=tmp_path/'release';output.mkdir();w.ROOT=output
    assert g.checkpoint(w,'release-observe',None,None,None)['ok']
    assert (g.WINDOW/'foreign-before.json').read_bytes()==before
    assert not (output/'foreign-before.json').exists()
    assert all('nudge' not in args[3:5] for _,args in s['calls'])
    lists=[args for _,args in s['calls'] if args[3:5]==['bd','list']]
    assert lists and all('--metadata-field' not in args and '--all' in args
                         and '--include-infra' in args and args[args.index('--limit')+1]=='4097' for args in lists)


def test_foreign_failure_does_not_prevent_containment_and_stays_sticky(tmp_path,monkeypatch):
    g,w,s=rig(tmp_path,monkeypatch)
    g.checkpoint(w,'preflight',None,None,None,capture=True,scoped=False)
    saved=s['queue']['dead'].pop()
    assert g.checkpoint(w,'city-suspend-after',None,None,None,fatal=False)['ok'] is False
    assert g.checkpoint(w,'rig-suspend-after',None,None,None,fatal=False)['ok'] is False
    s['queue']['dead'].append(saved)
    with pytest.raises(RuntimeError,match='prior foreign preservation failure'):
        g.checkpoint(w,'restore-admission',None,None,None)
    assert not (g.WINDOW/'foreign-restore-admission-pass.json').exists()


def test_earlier_baseline_required_and_no_second_capture(tmp_path,monkeypatch):
    g,w,s=rig(tmp_path,monkeypatch)
    with pytest.raises(FileNotFoundError):g.checkpoint(w,'release-without-preflight',None,None,None)
    assert not (g.WINDOW/'foreign-before.json').exists()


def test_epoch_drift_and_full_page_refuse(tmp_path,monkeypatch):
    g,w,s=rig(tmp_path,monkeypatch)
    g.checkpoint(w,'preflight',None,None,None,capture=True,scoped=False)
    s['session']='2';g.checkpoint(w,'first-session',None,None,None)
    s['session']='3'
    with pytest.raises(RuntimeError,match='session epoch changed'):
        g.checkpoint(w,'drifted-session',None,None,None)


def test_new_process_before_capture_refuses_without_baseline(tmp_path,monkeypatch):
    g,w,s=rig(tmp_path,monkeypatch)
    monkeypatch.setattr(g,'pollers',lambda w,s:[dict(pid=123)])
    with pytest.raises(RuntimeError,match='poller existed'):
        g.checkpoint(w,'preflight',None,None,None,capture=True,scoped=False)
    assert not (g.WINDOW/'foreign-before.json').exists()


def test_policy_pin_matches_exact_source():
    g=load('queue-guard.py')
    assert g.POLICY_SHA==hashlib.sha256((HERE/'queue-preservation.py').read_bytes()).hexdigest()


def test_owned_transition_during_shadow_read_is_not_foreign_drift(tmp_path,monkeypatch):
    g,w,s=rig(tmp_path,monkeypatch)
    g.checkpoint(w,'preflight',None,None,None,capture=True,scoped=False)
    s['session']='2';add_owned(s['queue'],s['beads'])
    before=copy.deepcopy(s['queue'])
    after=copy.deepcopy(before)
    own=next(row for row in after['pending'] if p.owned(row,SESSION))
    after['pending'].remove(own);after.setdefault('in_flight',[]).append(own)
    samples=iter([before,after,after,after])
    monkeypatch.setattr(g,'read_queue',lambda w:json.dumps(next(samples)).encode())
    assert g.checkpoint(w,'owned-race',None,None,None)['ok']


def test_transient_foreign_loss_at_first_endpoint_cannot_be_hidden(tmp_path,monkeypatch):
    g,w,s=rig(tmp_path,monkeypatch)
    g.checkpoint(w,'preflight',None,None,None,capture=True,scoped=False)
    damaged=copy.deepcopy(s['queue']);damaged['dead'].pop()
    samples=iter([damaged,s['queue']])
    monkeypatch.setattr(g,'read_queue',lambda w:json.dumps(next(samples)).encode())
    with pytest.raises(RuntimeError,match='foreign queue tuple changed'):
        g.checkpoint(w,'foreign-race',None,None,None)
    assert (g.WINDOW/'foreign-foreign-race-failure.json').is_file()
