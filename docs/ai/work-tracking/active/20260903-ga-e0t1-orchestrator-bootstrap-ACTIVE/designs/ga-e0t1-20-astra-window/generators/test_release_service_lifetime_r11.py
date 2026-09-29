"""Opt-in synthetic user-unit proof. Never touches Gas City or a provider.

Requires separate reviewed execution of this exact file. The two ephemeral units
own only these fixture processes; normal control-group teardown cleans helpers.
Evidence directories and all files remain. No direct signals or manual cleanup.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


def child(root):
    os.setpgid(0, 0)  # Native gc poller detaches its process group the same way.
    pid = os.getpid()
    start = Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split()[19]
    (root/'child.json').write_text(json.dumps(dict(pid=pid,start=start,
        pgid=os.getpgid(0),cgroup=Path('/proc/self/cgroup').read_text())))
    time.sleep(2)
    (root/'ack.json').write_text('{"delivered":true}\n')
    while True: time.sleep(1)


def parent(root, retain):
    subprocess.Popen([sys.executable,'-I','-B',__file__,'fixture-child',str(root)],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        close_fds=True)
    deadline=time.monotonic()+8
    while not (root/'child.json').exists():
        if time.monotonic()>deadline: raise RuntimeError('fixture helper did not start')
        time.sleep(.02)
    if retain:
        while not (root/'ack.json').exists():
            if time.monotonic()>deadline: raise RuntimeError('fixture acknowledgement absent')
            time.sleep(.02)
    (root/'parent.json').write_text(json.dumps(dict(retained=retain,
        cgroup=Path('/proc/self/cgroup').read_text(),ack=(root/'ack.json').exists())))


if __name__ == '__main__':
    mode, target = sys.argv[1:]
    root=Path(target)
    assert root.is_absolute() and str(root).startswith('/tmp/ga-e0t1-r11-lifetime-')
    assert root.resolve(strict=True)==root and root.stat().st_uid==os.getuid()==1000
    if mode=='fixture-child': child(root)
    elif mode in ('fixture-retain','fixture-exit'): parent(root,mode=='fixture-retain')
    else: raise RuntimeError('unknown fixture mode')
else:
    import pytest

    @pytest.mark.skipif(os.environ.get('GC_RELEASE_LIFETIME_PROOF')!='1',reason='reviewed opt-in synthetic unit only')
    @pytest.mark.parametrize('retain',[False,True])
    def test_real_user_oneshot_owns_detached_helper(tmp_path, retain):
        assert str(tmp_path).startswith('/tmp/ga-e0t1-r11-lifetime-')
        unit='ga-release-fixture-'+uuid.uuid4().hex
        args=['/usr/bin/systemd-run','--user','--quiet','--wait','--pipe','--collect',
            '--unit='+unit,'--property=Type=oneshot','--property=TimeoutStartSec=15s',
            '--property=TimeoutStopSec=5s','--property=KillMode=control-group',
            '--property=UMask=0077','/usr/bin/python3.12','-I','-B',str(Path(__file__).resolve()),
            'fixture-retain' if retain else 'fixture-exit',str(tmp_path)]
        env=dict(HOME='/home/loucmane',PATH='/usr/bin:/bin',XDG_RUNTIME_DIR='/run/user/1000',
            DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus',LANG='C.UTF-8')
        result=subprocess.run(args,env=env,cwd='/',capture_output=True,timeout=25)
        (tmp_path/'service-result.json').write_text(json.dumps(dict(argv=args,exit_code=result.returncode,
            stdout=result.stdout.decode(),stderr=result.stderr.decode())))
        assert result.returncode==0
        info=json.loads((tmp_path/'child.json').read_text())
        main=json.loads((tmp_path/'parent.json').read_text())
        assert info['pgid']==info['pid']
        assert info['cgroup']==main['cgroup'] and info['cgroup'].endswith('/'+unit+'.service\n')
        assert main['ack'] is retain and (tmp_path/'ack.json').exists() is retain
        # Verify native service teardown removed this exact process and cgroup.
        proc=Path('/proc')/str(info['pid'])
        assert not proc.exists() or proc.joinpath('stat').read_text().rsplit(') ',1)[1].split()[19]!=info['start']
        cgroup=Path('/sys/fs/cgroup')/info['cgroup'].strip().split('::',1)[1].lstrip('/')
        deadline=time.monotonic()+3
        while cgroup.exists() and time.monotonic()<deadline: time.sleep(.05)
        assert not cgroup.exists()
        (tmp_path/'proof.json').write_text(json.dumps(dict(ok=True,retain=retain,
            native_service_cleanup=True,zero_fixture_residue=True,gas_city_touched=False)))
