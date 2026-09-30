"""Execute only generated append control-flow with a disposable fake ledger."""
import copy
import json
from pathlib import Path
import types

import pytest

import window_r5 as r


@pytest.mark.parametrize('fault',[None,'before','after','ambiguous'])
def test_generated_amendment_one_append_and_no_replay(tmp_path,monkeypatch,fault):
    _,out=r.assemble(1790591514698290119)
    script=tmp_path/'startup-amendment-r5.py';script.write_bytes(out['startup-amendment-r5.py'])
    m=r.startup.source_module(script.read_bytes(),'amendment_execution_fixture')
    m.__file__=str(script);m._SOURCE_SHA=r.sha(script.read_bytes())
    m.HERE=tmp_path;m.ROOT=tmp_path/'result';m.WINDOW=tmp_path/'future-window'
    legacy=r.startup.source_module(out['legacy-continuation-r4.py'],'amendment_legacy')
    exact=r.startup.source_module(out['startup-amendment-contract-r5.py'],'amendment_exact')
    contract=r.startup.source_module(out['contract.py'],'amendment_task_contract')
    records={p:p.read_bytes() for p in legacy.PINS}
    state=json.loads(records[legacy.COMPLETED/'final.json'])
    amendment=json.loads(out['startup-amendment-r5.json'])
    if fault=='before':state['task']['status']='in_progress'
    w=types.SimpleNamespace(_SOURCE_SHA=None,GC=['/managed/gc','--city','fixture'],
        CITY=tmp_path/'city',RECEIPT=tmp_path/'receipt',CITY_SHA=['baseline'],RECEIPT_SHA=['baseline'],
        load_support=lambda:(None,None,None),pins=lambda:None,host=lambda o:{'host':'unchanged'})
    w.contract=lambda:contract
    calls=[];saved={}
    def read(path,pin=None):
        if path in records:raw=records[path]
        elif path.name=='startup-amendment-r5.json':raw=out[path.name]
        else:
            assert path in (w.CITY/'city.toml',w.RECEIPT)
            return b'unchanged'
        if pin is not None:assert r.sha(raw)==pin
        return raw
    w.read=read
    def module(path,pin):
        assert r.sha(out[path.name])==pin
        return legacy if path.name=='legacy-continuation-r4.py' else exact
    w.module=module
    def save(name,value):
        assert name not in saved
        saved[name]=copy.deepcopy(value)
        (w.ROOT/name).write_text(json.dumps(value))
    w.save=save;w.record=lambda name:saved[name]
    def phase(name,argv,*args,**kwargs):
        calls.append((name,argv))
        if 'show' in argv:
            bead=argv[argv.index('show')+1]
            return {'stdout':json.dumps([state['task' if bead==exact.TASK else 'parent']])}
        assert argv==w.GC+['--rig','gascity','bd','update',exact.TASK,'--append-notes',amendment['append_note']]
        state['task']['notes']+='\n'+amendment['append_note']
        state['task']['updated_at']='2026-09-28T12:40:00+00:00'
        [row]=[a for a in state['parent']['dependencies'] if a['id']==exact.TASK]
        for key in ('notes','updated_at'):row[key]=state['task'][key]
        if fault=='after':state['task']['extra']='unexplained'
        if fault=='ambiguous':raise RuntimeError('synthetic ambiguous write result')
        return {'stdout':''}
    w.phase=phase
    w.complete_containment=lambda:saved.setdefault('containment',True)
    def load(path,pin):
        assert path==tmp_path/'window-base-r11.py' and pin==r.sha(out['window-base-r11.py'])
        return w
    m.load=load
    if fault:
        with pytest.raises(RuntimeError):m.main()
        assert 'result.json' not in saved
    else:
        m.main()
        assert saved['result.json']['ok'] is True and saved['containment'] is True
    assert len([x for x in calls if x[0]=='append-startup-note'])==(0 if fault=='before' else 1)
    assert m.ROOT.exists() and not m.WINDOW.exists()
    count=len(calls)
    with pytest.raises(FileExistsError):m.main()
    assert len(calls)==count
