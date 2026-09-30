"""Execute only the extracted output-path guard in disposable fixtures, never a wrapper."""
import ast
from pathlib import Path
import subprocess

import pytest
from test_window_assembly import a, PARAMS

EXPECTED = {
    '/var/tmp/ga-mb91-integrity-20260930-r6',
    '/var/tmp/ga-mb91-window-20260930-r4',
    '/var/tmp/ga-mb91-audit-stage-20260930-r2',
    '/var/tmp/ga-mb91-audit-route-20260930-r2',
    '/var/tmp/ga-mb91-audit-resume-20260930-r2',
    '/var/tmp/ga-mb91-route-20260930-r2',
    '/var/tmp/ga-mb91-startup-release-20260930-r1',
    '/var/tmp/ga-mb91-terminal-20260930-r2',
    '/var/tmp/ga-mb91-candidate-inspection-20260930-r1',
}


def output():
    return a.assemble(**PARAMS)[1]


def guard(out):
    source=out['operator/OBSERVE.sh'].decode()
    first=source.index('# BEGIN fresh output admission\n')
    last=source.index('# END fresh output admission\n',first)
    assert last < source.index('step observe ')
    return source[first:last]


def test_complete_generated_fixed_root_inventory():
    out=output()
    assert set(a.fresh_output_roots(out))==EXPECTED
    text=guard(out)
    for path in EXPECTED:assert text.count(path)==1
    assert 'bind-20260930' not in text and 'prep-20260930' not in text
    assert b"ga-mb91-audit-%s-20260930-r2" in out['audit-queue-r3.py']
    assert b'ga-mb91-audit-route-20260930-r2/result.json' in out['operator/RESUME.sh']
    assert b'ga-mb91-audit-resume-20260930-r2' in out['operator/RESUME.sh']


def run_guard(tmp_path, occupied=None, kind='directory'):
    text=guard(output())
    replacements={p:tmp_path/Path(p).name for p in EXPECTED}
    for old,new in replacements.items():text=text.replace(old,str(new))
    if occupied:
        target=replacements[occupied]
        if kind=='directory':target.mkdir()
        elif kind=='file':target.write_text('preserved evidence')
        else:target.symlink_to(tmp_path/'absent-target')
    marker=tmp_path/'operation-reached'
    # No live command or generated wrapper is executed. The only write is this
    # fixture marker, reachable only if the actual shell guard permits it.
    result=subprocess.run(['/bin/sh','-c',text+'\n: > "'+str(marker)+'"'],capture_output=True,text=True)
    return result,marker,replacements


def test_all_absent_positive_reaches_fixture_operation(tmp_path):
    result,marker,_=run_guard(tmp_path)
    assert result.returncode==0 and marker.exists()


@pytest.mark.parametrize('occupied',sorted(EXPECTED))
def test_each_consumed_root_refuses_before_fixture_operation(tmp_path,occupied):
    result,marker,paths=run_guard(tmp_path,occupied)
    assert result.returncode!=0 and not marker.exists()
    assert paths[occupied].is_dir()


@pytest.mark.parametrize('kind',['file','dangling-symlink'])
def test_non_directory_collision_also_refuses_without_removal(tmp_path,kind):
    occupied='/var/tmp/ga-mb91-audit-stage-20260930-r2'
    result,marker,paths=run_guard(tmp_path,occupied,kind)
    assert result.returncode!=0 and not marker.exists()
    assert paths[occupied].is_symlink() if kind=='dangling-symlink' else paths[occupied].read_text()=='preserved evidence'


def test_missing_duplicate_or_nonliteral_root_is_not_inferred():
    out=output()
    for source in (b'ROOT = unknown()\n',b'ROOT = Path("/tmp/a")\nROOT = Path("/tmp/b")\n',b'pass\n'):
        changed=dict(out,**{'route-task.py':source})
        with pytest.raises(ValueError):a.fresh_output_roots(changed)


def test_final_materialized_fixed_roots_match_generated():
    out=output()
    from test_window_assembly import HERE
    actual={name:(HERE/name).read_bytes() for name in out}
    assert a.fresh_output_roots(actual)==a.fresh_output_roots(out)
