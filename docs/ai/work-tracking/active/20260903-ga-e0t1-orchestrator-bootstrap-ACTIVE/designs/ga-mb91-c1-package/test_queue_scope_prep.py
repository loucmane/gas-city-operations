"""Offline exact queue-scope preparation tests. No live operations."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tomllib
import types
import pytest

HERE=Path(__file__).parent
def prep():
    path=HERE/'prepare.py'
    m=types.ModuleType('prep_scope_test');m.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__)
    return m

def test_scope_is_exact_one_field_and_preserves_all_other_configuration():
    p=prep()
    raw=b'[session]\nstartup_timeout = "5m"\n[workspace]\nmax_active_sessions = 1\n'
    after=p.scoped_overlay(raw)
    before=tomllib.loads(raw.decode()); expected=copy.deepcopy(before)
    expected['session']['nudge_queue_scope']='session-epoch'
    assert tomllib.loads(after.decode())==expected
    assert after.replace(b'nudge_queue_scope = "session-epoch"\n',b'')==raw
    with pytest.raises(AssertionError): p.scoped_overlay(after)

@pytest.mark.parametrize('raw',[
    b'[workspace]\nmax_active_sessions=1\n',
    b'[session]\nnudge_queue_scope=""\n',
    b'[session]\nnudge_queue_scope="global"\n',
    b'[session]\nnudge_queue_scope="invalid"\n',
    b'[session]\nnudge_queue_scope="session-epoch"\n',
])
def test_scope_refuses_absent_or_preexisting_setting(raw):
    with pytest.raises((AssertionError,KeyError)): prep().scoped_overlay(raw)

@pytest.mark.parametrize('scope',[None,'global','invalid','session-epoch',0,False])
def test_effective_scope_refuses_any_nonbaseline_value(scope):
    with pytest.raises(AssertionError): prep().scoped_config({'config':{'Session':{'NudgeQueueScope':scope}}})

def test_effective_scope_does_not_mutate_input_or_relax_prompt_contract():
    value={'config':{'Session':{'NudgeQueueScope':'','StartupTimeout':'5m'},'Agents':[{'keep':'exact'}]}}
    original=copy.deepcopy(value)
    changed=prep().scoped_config(value)
    assert value==original
    assert changed['config']['Session'].pop('NudgeQueueScope')=='session-epoch'
    original['config']['Session'].pop('NudgeQueueScope')
    assert changed==original
    prior=HERE.parent/'ga-jcxb-c1-package/launch-contract.py'
    assert prior.read_bytes().replace(b'ga-jcxb',b'ga-mb91')==(HERE/'launch-contract.py').read_bytes()

def test_observed_core_serialization_is_exactly_the_new_default_field():
    p=prep()
    frozen=json.loads((HERE.parent/'ga-e0t1.20-astra-bootstrap/inputs.json').read_bytes())
    raw={k:base64.b64decode(v,validate=True) for k,v in frozen.items()}
    expected=json.loads(p.retarget(raw)['config.baseline.json'])
    actual=json.loads(Path('/tmp/ga-mb91-prep-input-observation-20260930-r1/config.baseline.json').read_bytes())
    assert actual==expected
    raw['config.baseline.json']=json.dumps(actual).encode()
    with pytest.raises(AssertionError): p.retarget(raw)

def test_actual_uninstalled_preparation_binds_scope_and_adopted_inputs():
    p=prep(); old=p.configure()
    source=HERE.parent/'ga-e0t1.20-astra-bootstrap/inputs.json'
    raw={k:base64.b64decode(v,validate=True) for k,v in json.loads(source.read_bytes()).items()}
    baseline=json.loads(p.retarget(raw)['config.baseline.json'])
    orders=json.loads(raw['orders.baseline.json'])
    overlay,patches,names,target,selected=old.build_overlay(old.read(old.CITY/'city.toml',old.CITY_SHA),baseline,orders)
    effective=old.expected_config(baseline,selected,target,names)
    assert tomllib.loads(overlay.decode())['session']['nudge_queue_scope']=='session-epoch'
    assert effective['config']['Session']['NudgeQueueScope']=='session-epoch'
    assert old.sha(overlay)==old.OVERLAY_SHA
    for path,digest in [(old.GC,old.GC_SHA),(old.COMPOSE,old.COMPOSE_SHA),
                        (old.BUILD/'compose',old.FINALIZE_SHA),(old.PRIOR,old.PRIOR_SHA),
                        (old.RECEIPT,old.RECEIPT_SHA),(old.BUILD/'phase_runner.py',old.RUNNER_PHASE_SHA)]:
        assert hashlib.sha256(old.read(path)).hexdigest()==digest
    assert len(patches)==48 and 'nudge-on-route' not in names
    assert old.GC_SHA=='5802a35645280790f1cda16dff3c71445be7146e42021f3be5fd481e79138444'
    assert old.RECEIPT_SHA=='2607e90522b5571a5180d882e3d21882bafbc42423e0855f11fae7ec00bdf980'
    # Configuration/byte proof only. No baseline config command, child, worker or live adoption runs.
