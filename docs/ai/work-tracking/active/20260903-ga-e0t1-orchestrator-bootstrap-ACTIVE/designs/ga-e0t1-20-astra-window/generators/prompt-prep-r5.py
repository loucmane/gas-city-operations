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
ROOT=Path('/var/tmp/ga-e0t1.20-prompt-prep-20260928-r5')
PROMPT=HERE/'PRECLAIM-R5.md'
PROMPT_SHA='R5_PROMPT_SHA'
HELPER_SHA='R5_HELPER_SHA'
RECOVERY=Path('/var/tmp/ga-e0t1.20-terminal-20260928-r4/result.json')
RECOVERY_SHA='459cacbbaf67e60f741af656277ebf11161a4abe3bab49637e7407db40f16438'


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
    assert recovered['worker_started_in_window'] is True and recovered['source_release_sent'] is False
    assert recovered['open_sessions']==0
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
                recovery_result_sha256=RECOVERY_SHA,supplemental_prompt_preparation=True,
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
