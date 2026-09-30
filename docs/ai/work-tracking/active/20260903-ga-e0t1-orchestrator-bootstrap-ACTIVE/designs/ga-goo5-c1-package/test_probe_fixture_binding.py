"""Cross-component sandbox-negative fixture binding; assembly only, no host I/O."""
import ast
from pathlib import Path
import types

import pytest

HERE=Path(__file__).parent
a=types.ModuleType('window_assembly');a.__file__=str(HERE/'window-assembly.py')
exec(compile((HERE/'window-assembly.py').read_bytes(),a.__file__,'exec'),a.__dict__)
PARAMS=dict(observation='/tmp/ga-goo5-readonly-baseline-20260930-r1/observed.json',
            observation_sha='a'*64,cache_ns=1790725229209043845)


def literal_path(raw,name):
    nodes=[n.value for n in ast.parse(raw).body if isinstance(n,ast.Assign)
           and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name]
    assert len(nodes)==1
    value=nodes[0]
    assert isinstance(value,ast.Call) and isinstance(value.func,ast.Name) and value.func.id=='Path'
    assert len(value.args)==1 and not value.keywords
    return Path(ast.literal_eval(value.args[0]))


def verify(out):
    foreign=literal_path(out['worker-startup.py'],'FOREIGN')
    root=literal_path(out['bind-task.py'],'ROOT')
    route=literal_path(out['route-task.py'],'BIND')
    assert foreign==root/'sandbox-negative'
    assert route==root
    wrapper=out['operator/BIND.sh'].decode()
    assert '[ ! -e '+str(root)+' ] && [ ! -L '+str(root)+' ]' in wrapper
    assert "(ROOT/'sandbox-negative').mkdir(mode=0o700)" in out['bind-task.py'].decode()


def test_prepared_probe_and_all_fixture_producers_match():
    verify(a.assemble(**PARAMS)[1])


@pytest.mark.parametrize('name', ['worker-startup.py','bind-task.py','route-task.py','operator/BIND.sh'])
def test_any_one_component_mismatch_is_detected(name):
    out=dict(a.assemble(**PARAMS)[1])
    out[name]=out[name].replace(b'ga-goo5-bind-20260930-r1',b'ga-goo5-bind-wrong')
    with pytest.raises(AssertionError):
        verify(out)
