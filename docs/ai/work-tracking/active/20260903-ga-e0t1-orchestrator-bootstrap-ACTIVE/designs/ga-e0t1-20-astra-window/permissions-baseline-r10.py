"""Read-only exact R9 successor; no permissions, inventory or transcript writes."""
import copy
import json
import os
from pathlib import Path
import stat

HERE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window')
PRIOR_SHA='12190b7a5d387b37a922e1b50f30a363869489366b65332894a40a658b48446d'
CAPTURE=Path('/tmp/ga-e0t1-r10-permission-capture-20260929')
IMAGES_SHA='59521dd6056d3d67ca60f87f1b42cea4ce9e9ec4b9648188c742358211c66b48'
HISTORY_SHA='31b1af6ba05b6baaaf97d049ebd9f59b63d5353558ba869bce012c786965f14d'
DAY='/home/loucmane/.codex/sessions/2026/09/29'
TRANSCRIPT=DAY+'/rollout-2026-09-29T01-28-56-01a0ea59-9af7-7aa1-a484-2797e9b282d1.jsonl'
TRANSCRIPT_SHA='429a0c47118e51df7d5d805039a00e4b4b56de6c83544970cd969ab86911a3ad'
POSTIMAGE_SHA='709e74b448d50a0f4fc5a3fcaa7fc1728b5b364cfe8a76082ffe90cbd7e03010'
RESULT_SHA='baae65a63de589bc354a11d8ea673bded479be63aa004170256430073c44c862'
TERMINAL=Path('/var/tmp/ga-e0t1.20-terminal-20260929-r9/result.json')
TERMINAL_SHA='dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'


def expected(prior, postimage, history, images, current_history, private):
    old=prior.expected_postimage(postimage)
    assert set(images)==set(old)|{prior.TRANSCRIPT,DAY,TRANSCRIPT}
    parent=str(Path(DAY).parent)
    for p,before in old.items():
        value=copy.deepcopy(images[p])
        if p==parent:
            assert value['stat']['mtime_ns']==value['stat']['ctime_ns']==1790638136417488525
            assert value['stat']['nlink']==before['stat']['nlink']+1
            for k in ('mtime_ns','ctime_ns','nlink'):value['stat'][k]=before['stat'][k]
        assert value==before,'permission baseline changed: '+p
    assert images[prior.TRANSCRIPT]==dict(stat=prior.TRANSCRIPT_STAT,xattrs={},sha256=prior.TRANSCRIPT_SHA)
    assert images[DAY]['stat']['mode']==0o40700 and images[DAY]['xattrs']=={'system.posix_acl_default':private.hex()}
    assert images[TRANSCRIPT]['stat']['mode']==0o100600 and images[TRANSCRIPT]['xattrs']=={}
    assert images[TRANSCRIPT]['sha256']==TRANSCRIPT_SHA
    baseline=copy.deepcopy(history)
    for section in ('rules','sessions'):
        for p in baseline[section]:
            if p in old:baseline[section][p]=images[p]['stat']
    assert all(p not in baseline['sessions'] for p in (prior.TRANSCRIPT,DAY,TRANSCRIPT))
    for p in (prior.TRANSCRIPT,DAY,TRANSCRIPT):baseline['sessions'][p]=images[p]['stat']
    assert baseline==current_history,'historical inventory changed'
    return images,baseline


def verify(read,module):
    prior=module(HERE/'permissions-baseline-r9.py',PRIOR_SHA,'prior_permission_baseline')
    result=json.loads(read(Path(prior.RESULT),RESULT_SHA))
    assert result.get('ok') is True and result.get('worker_release') is False
    assert result.get('historical_transcripts_modified') is False
    assert result.get('creation_proof',{}).get('all_private') is True
    assert result['creation_proof'].get('unchanged_strict_rules_reader_pass') is True
    for p,pin in ((prior.TERMINAL,prior.TERMINAL_SHA),(TERMINAL,TERMINAL_SHA)):
        terminal=json.loads(read(p,pin))
        assert all(terminal.get(k) is True for k in ('ok','actual_host_verified','accepted_restoration_bound','terminal_suspension_endpoint_bound'))
    m=module(prior.SOURCE,prior.SOURCE_SHA,'accepted_permissions_reader')
    images,history=expected(prior,json.loads(read(Path(prior.POSTIMAGE),POSTIMAGE_SHA)),
        json.loads(read(prior.HISTORY,prior.HISTORY_SHA)),json.loads(read(CAPTURE/'images.json',IMAGES_SHA)),
        json.loads(read(CAPTURE/'history.json',HISTORY_SHA)),m.PRIVATE)
    entries={}
    try:
        for p,before in images.items():
            fd=m.open_exact(p,directory=stat.S_ISDIR(before['stat']['mode']));entries[p]=fd
            m.stable_identity(p,fd)
            assert m.image(fd)==before,'exact postimage drift: '+p
        for section in ('rules','sessions'):
            assert m.inventory('/home/loucmane/.codex/'+section)==history[section],'historical inventory drift'
        for p,fd in entries.items():
            m.stable_identity(p,fd)
            assert m.image(fd)==images[p],'postimage changed during proof'
    finally:
        for fd in entries.values():os.close(fd)
