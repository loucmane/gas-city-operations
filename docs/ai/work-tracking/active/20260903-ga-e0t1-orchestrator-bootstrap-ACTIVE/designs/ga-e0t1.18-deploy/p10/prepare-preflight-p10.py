"""Reuse reviewed exact-source builder, adding unchanged production probes.

P10: the P8 preflight builder (277901e3) with fresh roots and the P10 preflight-main.go (make_p10.py).

Only isolated build/evidence paths change. No provider/version/auth/signer
invocation occurs while preparing this diagnostic.
"""
import hashlib
import json
from pathlib import Path
import types

HERE = Path(__file__).parent
BUILDER = HERE.parent/'p8'/'prepare-compose-p8.py'
EXPECTED = '56f3ca480c31e2ffbf525ff4e3b77b354ecbb097088a9072c11372b03b5400a4'
PRIOR = Path('/var/tmp/ga-e0t1.18-compose-diagnostic-20260926')
ROOT = Path('/var/tmp/ga-e0t1.18-p10-preflight-diagnostic-20260926')
STAGING = Path('/var/tmp/ga-e0t1.18-p10-preflight-generated-20260926')
GROUPS = (
 ('cmd/gc/managed_worker_preflight.go',('defaultManagedWorkerPreflightProbes',
  'readManagedControlPolicy','probeManagedWorkerToolchain','overlayEnvironment','probeManagedWorkerSigner')),
 ('internal/api/handler_provider_readiness.go',('findProbeBinary','providerProbeSearchDirs','providerProbeSearchPath')),
)

def sha(raw):return hashlib.sha256(raw).hexdigest()

def main():
    raw=BUILDER.read_bytes()
    if sha(raw)!=EXPECTED:raise RuntimeError('reviewed builder drift')
    builder=types.ModuleType('reviewed_exact_builder');builder.__file__=str(BUILDER)
    exec(compile(raw,str(BUILDER),'exec',dont_inherit=True),builder.__dict__)
    inventory=json.loads((PRIOR/'inventory.json').read_bytes())['stdout']
    builder.verify_archive(PRIOR/'source',inventory,diagnostic=True)
    # The old inventory itself is bound to the archived exact commit/tree.
    # The fresh builder independently re-verifies all source objects afterward.
    pieces=[(HERE/'preflight-main.go').read_text()]
    bindings=[]
    for relative,names in GROUPS:
        path=PRIOR/'source'/relative
        text=path.read_text()
        for name in names:
            start=text.index('func '+name+'(')
            end=text.index('\n}\n',start)+3
            segment=text[start:end]
            pieces.append(segment)
            bindings.append(dict(path=relative,name=name,sha256=sha(segment.encode())))
    main_source='\n\n'.join(pieces)+'\n'
    STAGING.mkdir(mode=0o700)
    (STAGING/'compose-main.go').write_text(main_source)
    (STAGING/'extraction.json').write_text(json.dumps(dict(
        source_commit=builder.COMMIT, reviewed_builder_sha256=EXPECTED,
        main_template_sha256=sha((HERE/'preflight-main.go').read_bytes()),
        generated_main_sha256=sha(main_source.encode()),functions=bindings,
        provider_invoked=False,signer_invoked=False),indent=2,sort_keys=True)+'\n')
    builder.ROOT=ROOT
    builder.HERE=STAGING
    builder.main()
    # Each copied function must also be byte-identical in the fresh archive.
    for relative,names in GROUPS:
        fresh=(ROOT/'source'/relative).read_bytes()
        if fresh!=(PRIOR/'source'/relative).read_bytes():
            raise RuntimeError('fresh production extraction source mismatch')
    (ROOT/'extraction.json').write_bytes((STAGING/'extraction.json').read_bytes())

if __name__=='__main__':main()
