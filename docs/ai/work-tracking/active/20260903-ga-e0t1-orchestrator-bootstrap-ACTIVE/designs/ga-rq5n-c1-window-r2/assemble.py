"""Pure append-forward assembly after an exact pre-staging refusal.

No execution or writing entry point. Completed WORKTREE, PREP and BIND stay
consumed. Operational roots alone advance to r2; prepared worker inputs stay
byte-identical. Queue admission is unchanged. One frozen supported ledger
disposition is reconciled before the already-reviewed two-edge route comparison.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import types

HERE = Path(__file__).parent
OLD = HERE.parent / "ga-rq5n-c1-package"
MANIFEST_SHA = "9d3d481c8b9fd11d08c0b1896b2cab4e2b5694c9846ae68a38c2cdf1b9f35f25"
DISPOSITION_SHA = "794b7dae9abaab30c11560e02875f2e193ad5ffea97620c653af0417b0da7e51"
EXCLUDED = {"bind-task.py", "operator/BIND.sh"}
LOCAL = {
    "contract.py", "startup-validation.py", "worker-startup.py", "PRECLAIM.md",
    "WORKER-BRIEF.md", "permissions-baseline.py", "launch-contract.py",
    "fresh-admission.py", "fresh-workspace.py", "FILE-SCOPE.json", "create-only-patch.py",
}
OLD_OBSERVATION = "/tmp/ga-rq5n-readonly-baseline-20260929-r2/observed.json"
OLD_OBSERVATION_SHA = "e190b13084d0f85eee7d669abb9831eaebb23002b6b8ce13ea05c33b2f6245ac"
OLD_CACHE_NS = 1790698733306040648

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load(raw, name, path):
    value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(raw,str(path),"exec",dont_inherit=True),value.__dict__)
    return value

def once(text, old, new):
    if text.count(old)!=1: raise ValueError("missing or ambiguous anchor "+old[:80])
    return text.replace(old,new)

def replace_function(text, name, replacement):
    nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name]
    if len(nodes)!=1:raise ValueError("function anchor")
    [n]=nodes;lines=text.splitlines(keepends=True)
    return "".join(lines[:n.lineno-1])+replacement.rstrip()+"\n"+"".join(lines[n.end_lineno:])

def retarget(text):
    text=text.replace("ga-rq5n-c1-package","ga-rq5n-c1-window-r2")
    def root(match):
        return match[0] if match["phase"] in ("prep","bind","worktree") else match[0][:-2]+"r2"
    text=re.sub(r"/var/tmp/ga-rq5n-(?P<phase>[a-z%0-9.-]+)-20260929-r1",root,text)
    text=text.replace("ga-rq5n-r1-","ga-rq5n-r2-")
    return text

CONTINUED = """def continued_task(current,bound,w):
    # Retain the genuine completed BIND record; account for only the exact
    # supported blocking disposition made after the pre-staging refusal.
    import copy
    d=json.loads(w.read(HERE/'held-predecessor-disposition.json',DISPOSITION_SHA))
    assert set(d)=={'schema','task','before_projection','after_projection','allowed_fields',
                    'actual_delta','source_preserved','review_outcome','pass_closeout'}
    assert d['schema']=='ga-rq5n.held-predecessor-disposition.v1' and d['task']=='ga-9olv'
    assert d['review_outcome']=='HOLD' and d['pass_closeout'] is False and d['source_preserved'] is True
    assert d['allowed_fields']==d['actual_delta']==['status','updated_at']
    a,z=d['before_projection'],d['after_projection']
    assert set(a)==set(z) and a['status']=='open' and z['status']=='blocked'
    assert {k:v for k,v in a.items() if k not in d['allowed_fields']}=={
            k:v for k,v in z.items() if k not in d['allowed_fields']}
    from datetime import datetime
    assert datetime.fromisoformat(z['updated_at'])>=datetime.fromisoformat(a['updated_at'])
    expected=copy.deepcopy(bound)
    rows=expected['dependencies']
    assert len(rows)==2 and {row['id'] for row in rows}=={'ga-e0t1','ga-9olv'}
    [index]=[i for i,row in enumerate(rows) if row['id']=='ga-9olv']
    assert rows[index]==a,'historical BIND projection differs from disposition preimage'
    rows[index]=copy.deepcopy(z)
    admission=w.module(HERE/'fresh-admission.py',ADMISSION_SHA)
    admission.continued_task(current,expected,w.contract())
"""

def assemble(*, observation, observation_sha, cache_ns):
    if re.fullmatch(r"/tmp/ga-rq5n-readonly-baseline-20260929-r[3-9][0-9]*/observed.json",observation) is None:
        raise ValueError("fresh post-reconciliation observation required")
    if re.fullmatch("[0-9a-f]{64}",observation_sha) is None or type(cache_ns) is not int or cache_ns<=0:
        raise ValueError("exact fresh pins required")
    raw=(OLD/"assembly.json").read_bytes()
    if sha(raw)!=MANIFEST_SHA:raise ValueError("R1 manifest drift")
    manifest=json.loads(raw)
    before={n:(OLD/n).read_bytes() for n in manifest["files"]}
    if any(sha(b)!=manifest["files"][n] for n,b in before.items()):raise ValueError("R1 file drift")
    disposition=(HERE/"held-predecessor-disposition.json").read_bytes()
    if sha(disposition)!=DISPOSITION_SHA:raise ValueError("ledger disposition drift")
    source=(OLD/"window-assembly.py").read_bytes()
    # This helper is a pure fixed-point SHA rebinder already reviewed in R1.
    if sha(source)!="12ff39bd8b5336f0e85214ab337734b19221b8c83c63daea19a76c27ce2fa93c":raise ValueError("R1 assembler drift")
    helper=load(source,"r1_assembler",OLD/"window-assembly.py")
    out={n:(b if n in LOCAL else retarget(b.decode()).encode()) for n,b in before.items() if n not in EXCLUDED}
    base=out["window-base.py"].decode()
    base=once(base,repr(OLD_OBSERVATION),repr(observation))
    base=once(base,repr(OLD_OBSERVATION_SHA),repr(observation_sha))
    base=once(base,"CACHE_PREV_NS = "+str(OLD_CACHE_NS),"CACHE_PREV_NS = "+str(cache_ns))
    base=once(base,"CACHE_PINNED_NS = "+str(OLD_CACHE_NS),"CACHE_PINNED_NS = "+str(cache_ns))
    out["window-base.py"]=base.encode()
    route=out["route-task.py"].decode()
    route=replace_function(route,"continued_task",CONTINUED)
    route=once(route,"    continued_task(before,bound)","    continued_task(before,bound,w)")
    route=once(route,"TARGET='gascity/codex'",
        "TARGET='gascity/codex'\nDISPOSITION_SHA="+repr(DISPOSITION_SHA)+"\nADMISSION_SHA="+repr(sha(before["fresh-admission.py"])))
    out["route-task.py"]=route.encode()
    out["held-predecessor-disposition.json"]=disposition
    out=helper.rebind(out,before,{},LOCAL|{"held-predecessor-disposition.json"})
    if any(out[n]!=before[n] for n in LOCAL):raise ValueError("prepared worker input changed")
    for name,body in out.items():
        if name.endswith(".py"):ast.parse(body,filename=name)
    return before,out
