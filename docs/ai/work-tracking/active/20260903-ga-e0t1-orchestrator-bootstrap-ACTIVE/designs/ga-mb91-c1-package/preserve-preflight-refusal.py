"""Preserve only the exact ga-mb91 PREFLIGHT historical shadow refusal; never replay or queue."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT=Path('/home/loucmane/.local/share/gas-city-staging/jobs')
O='/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
CANDIDATE,job,halt_sha,done_sha=sys.argv[1:]
assert re.fullmatch('[0-9a-f]{40}',CANDIDATE)
JOB_COMMITS={'ga-mb91-preflight-r1':'60bfdcc0761767f1e81a692e19f43e068efae009'}
EXPECTED_EXIT=1
assert job in JOB_COMMITS
assert all(re.fullmatch('[0-9a-f]{64}',v) for v in (halt_sha,done_sha))
assert os.getuid()==os.geteuid()==1000
assert not os.path.lexists(ROOT/'PAUSE') and not list((ROOT/'queue').iterdir())
for arguments,expected in [(['rev-parse','HEAD'],CANDIDATE),(['status','--porcelain','--untracked-files=all'],'')]:
    result=subprocess.run(['/usr/bin/git','--no-optional-locks','-C',O,*arguments],check=True,capture_output=True,text=True)
    assert result.stdout.strip()==expected
relative=str(Path(__file__).resolve().relative_to(Path(O)))
blob=subprocess.run(['/usr/bin/git','--no-optional-locks','-C',O,'show',CANDIDATE+':'+relative],
    check=True,capture_output=True).stdout
assert blob==Path(__file__).read_bytes(),'halt helper differs from signed candidate'
signed=subprocess.run(['/usr/bin/git','--no-optional-locks','-C',O,'verify-commit','--raw',CANDIDATE],
    capture_output=True,text=True)
assert signed.returncode==0 and '[GNUPG:] VALIDSIG ' in signed.stderr
assert '7720D1FE503A88EDECA61A6F0C7D823543E01875' in signed.stderr
failed=Path('/var/tmp/ga-mb91-window-20260930-r1')
manifest=Path(__file__).with_name('PREFLIGHT-REFUSAL-R1.json')
assert hashlib.sha256(manifest.read_bytes()).hexdigest()=='c5fe7abb1a53a0f6be1d1f008498e38b95940701546ead4eec930c4eff2230ed'
expected=json.loads(manifest.read_bytes())
assert not {'preflight-pass.json','stage-consumed.json','stage-pass.json'} & expected.keys()
assert set(p.name for p in failed.iterdir())==set(expected),'refusal phase advanced'
for name,item in expected.items():
    fd=os.open(failed/name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_NONBLOCK)
    try:
        st=os.fstat(fd)
        assert stat.S_ISREG(st.st_mode) and st.st_uid==1000 and st.st_nlink==1
        assert stat.S_IMODE(st.st_mode)==item['mode'] and st.st_size<16<<20
        with os.fdopen(os.dup(fd),'rb') as stream: raw=stream.read()
        assert hashlib.sha256(raw).hexdigest()==item['sha256'] and os.fstat(fd)==st
    finally:os.close(fd)
assert not os.path.lexists('/var/tmp/ga-mb91-window-20260930-r2'),'successor already started'
assert json.loads((failed/'foreign-preflight-failure.json').read_bytes())==dict(
    error='queue backing Bead missing',queue_or_beads_restored=False,replay=False)
for name in expected:
    if name.endswith('-phase.json'):
        phase=json.loads((failed/name).read_bytes())
        assert phase['exit_code']==0 and not phase['timed_out']
        cleanup=phase['cleanup']
        assert cleanup['owned_process_group_gone'] and cleanup['direct_child_reaped']
        assert not cleanup['failures'] and not cleanup['unexpected_survivors']
for path,pin in [
    ('/tmp/ga-mb91-queue-readback-diagnostic-20260930-r3/result.json','ac4d8a2b030746985e2182d6f72a09f681bc1bddbf88857cc3f3111e0256d159'),
    ('/tmp/ga-mb91-queue-readback-diagnostic-20260930-r4/result.json','3fe78efb4d66cad3ecb117f8dcd60376c405cc62df659f5a211599279feec289')]:
    raw=Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==pin
    evidence=json.loads(raw)
    assert evidence['ok'] and evidence['protected_non_atime_unchanged']
    assert evidence['failed_preflight_pre_mutation'] and evidence['latch_unchanged']
    assert evidence['worker_launched'] is False
assert not os.path.lexists('/var/tmp/ga-mb91-route-20260930-r1'),'task already routed'
assert hashlib.sha256(Path('/var/tmp/ga-mb91-bind-20260930-r1/result.json').read_bytes()).hexdigest()=='02cedf2952f9839e88b9599414f3ba4eb58751cbc026753ebc2b4f668fe0a25d'
path=ROOT/'done'/f'{job}.json'
fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_NONBLOCK)
try:
    s=os.fstat(fd)
    assert stat.S_ISREG(s.st_mode) and s.st_uid==1000 and s.st_nlink==1 and s.st_size<65536
    raw=os.read(fd,65536)
    assert len(raw)==s.st_size and hashlib.sha256(raw).hexdigest()==done_sha
finally:os.close(fd)
done=json.loads(raw)
assert done['exit']==EXPECTED_EXIT and done['unit_state_after']=='inactive'
assert done['job']['job_id']==job and done['job']['commit']==JOB_COMMITS[job]
result=subprocess.run(['/usr/bin/systemctl','--user','is-active',f'gc-job-{job}.service'],capture_output=True,text=True)
assert result.stdout.strip()=='inactive' and not result.stderr
assert json.loads((ROOT/'state/runner.json').read_bytes())['state']=='halted'
directory=os.open(ROOT/'state',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
archive=f'HALTED.{job}.adjudicated'
try:
    ds=os.fstat(directory)
    assert ds.st_uid==1000 and not ds.st_mode&0o022
    fd=os.open('HALTED',os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME,dir_fd=directory)
    try:
        before=os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_uid==1000
        assert stat.S_IMODE(before.st_mode)==0o600 and before.st_size<1024
        raw=os.read(fd,1024)
        assert len(raw)==before.st_size and hashlib.sha256(raw).hexdigest()==halt_sha
        assert json.loads(raw)['reason']==f'job {job} finished with exit {EXPECTED_EXIT}; read its log, record the outcome, then clear'
        assert os.stat('HALTED',dir_fd=directory,follow_symlinks=False)==before
        libc=ctypes.CDLL(None,use_errno=True)
        rename=libc.renameat2
        rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        rename.restype=ctypes.c_int
        assert rename(directory,b'HALTED',directory,archive.encode(),1)==0,ctypes.get_errno()
        os.fsync(directory)
        assert os.stat(archive,dir_fd=directory,follow_symlinks=False).st_ino==before.st_ino
    finally:os.close(fd)
finally:os.close(directory)
assert not os.path.lexists(ROOT/'state/HALTED')
assert hashlib.sha256((ROOT/'state'/archive).read_bytes()).hexdigest()==halt_sha
print(json.dumps(dict(archived=archive,job=job,no_job_queued=True)))

