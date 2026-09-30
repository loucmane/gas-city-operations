"""Supplemental uninstalled prompt preparation; not a repeat of S1 PREP.

Only scratch artifacts are written. Existing S1 preparation, r4 results and
restoration stay immutable. Native normalization and finalization produce the
new receipt. No receipt, trust, permission, city or lifecycle is installed.
"""
import hashlib
import json
from pathlib import Path
import sys
import types

HERE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window')
SEED=HERE.parent/'ga-e0t1.20-astra-bootstrap/prepare.py'
SEED_SHA='40858f94e795425c38f1e5ae8b973aa60e5c3aa67043bc84b6be36389b4ea6c3'
ROOT=Path('/var/tmp/ga-e0t1.20-prompt-prep-20260928-r6')
PROMPT=HERE/'PRECLAIM-R6.md'
PROMPT_SHA='fafd2012a531c99534ce69112adc0976fb437da9a8193d20d738b5535f94194d'
HELPER_SHA='cfd2467d3ce7c8600eb635d28a97249ccdc7bfa055386a423506d3f8e60edc7e'
RECOVERY=Path('/var/tmp/ga-e0t1.20-terminal-20260928-r5/result.json')
RECOVERY_SHA='dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'


def configure():
    raw=SEED.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==SEED_SHA,'preparation source drift'
    seed=types.ModuleType('r5_prep_seed');seed.__file__=str(SEED)
    exec(compile(raw,str(SEED),'exec',dont_inherit=True),seed.__dict__)
    inherited=seed.load()
    native_receipt_image=inherited.receipt_image
    old=seed.configure(inherited)
    old.read(PROMPT,PROMPT_SHA)
    helper=old.module(HERE/'launch-contract-r5.py',HELPER_SHA,'launch_contract')
    recovered=json.loads(old.read(RECOVERY,RECOVERY_SHA))
    assert all(recovered.get(k) is True for k in ('ok','actual_host_verified',
        'terminal_suspension_endpoint_bound','accepted_restoration_bound'))
    closed=json.loads(old.read(Path('/var/tmp/ga-e0t1.20-r5-close-20260928T130452Z/result.json'),'53b7501005e7f48722f022e023995ba6c9c8b83f3e7adcfa4c6d9e6089da46ea'))
    assert closed == dict(ok=True,closed_session='ci-rks41',open_sessions=0,
        city_tmux_sessions=0,worktree_processes=0,tmux_server_killed=False,signals_sent=False,
        executor_sha256='33f22aafa01ac42f7589c6f856e3bae06baaec93a60233ee3f167ffc3adaff40')
    assert not Path('/var/tmp/ga-e0t1.20-startup-release-20260928-r5/proof.json').exists()
    # The terminal observer launched none; its result is not relabeled
    # as proof that the completed R5 window had no worker.
    old.ROOT=ROOT
    original_build=old.build_overlay
    original_expected=old.expected_config

    def build(city,baseline,orders):
        raw,patches,names,target,selected=original_build(city,baseline,orders)
        marker=b'[[patches.agent]]\ndir = "gascity"\nname = "codex"\nsuspended = false\n'
        assert raw.count(marker)==1,'target prompt patch is not unique'
        changed=raw.replace(marker,marker+('prompt_template = '+json.dumps(str(PROMPT))+'\n').encode())
        old.OVERLAY_SHA=old.sha(changed)
        return changed,patches,names,target,selected

    def expected(*args):
        value=original_expected(*args)
        import copy
        changed=copy.deepcopy(value)
        [target]=[a for a in changed['config']['Agents'] if (a['Dir'],a['Name'])==('gascity','codex')]
        target['PromptTemplate']=str(PROMPT)
        helper.config_delta(value,changed,str(PROMPT))
        return changed

    def image(*args):
        # Preserve every typed-profile check from S1. Replace only its obsolete
        # isolated revision literal with the observed native composition value.
        before=json.loads(old.read(old.RECEIPT,old.RECEIPT_SHA))
        names={p['name'] for p in before['profiles']}
        assert names=={'gascity/gc.implementation-worker','gascity/operations-candidate-worker',
            'gas-city-template/gc.implementation-worker'} and len(before['profiles'])==3
        raw=native_receipt_image(*args)
        final=json.loads(raw)
        assert final['profiles']==before['profiles'],'typed profiles changed'
        observed=json.loads(old.read(ROOT/'composition.after.json'))
        assert final['permission_revision']==observed['permission_revision'],'native revision drift'
        return raw

    # main also requires the complete native receipt delta to be exactly
    # permission_revision and receipt_sha256. Nothing is installed here.
    old.build_overlay=build
    old.expected_config=expected
    old.receipt_image=image
    original_write=old.write

    def write(name,data,root=None):
        if name=='result.json':
            data=dict(data,prompt_path=str(PROMPT),prompt_sha256=PROMPT_SHA,
                recovery_result_sha256=RECOVERY_SHA,prior_close_sha256='53b7501005e7f48722f022e023995ba6c9c8b83f3e7adcfa4c6d9e6089da46ea',
                supplemental_prompt_preparation=True,
                prior_preparation_preserved=True)
        return original_write(name,data,root)

    old.write=write
    old._SOURCE_SHA=globals().get('_SOURCE_SHA')
    return old


if __name__=='__main__':
    old=configure()
    assert old._SOURCE_SHA and old.read(Path(__file__),old._SOURCE_SHA),'source launcher required'
    if len(sys.argv)==3 and sys.argv[1]=='normalize':old.normalize_main(Path(sys.argv[2]))
    else:
        assert len(sys.argv)==1
        old.main()
