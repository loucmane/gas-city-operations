"""P10 candidate composition diagnostic: the reviewed P8 exact-source builder, unchanged, into a fresh root.

Only the root and the composition source change. compose-main.go is the P8 source (e8cb87a0) with the target
moved to gascity/operations-candidate-worker, the claude-candidate provider and its PATH override (make_p10.py).
The builder records the Core commit, tree, archive, Go executable and the source digest in build-result.json.
"""
import hashlib
from pathlib import Path
import types

HERE = Path(__file__).parent
BUILDER = HERE.parent/'p8'/'prepare-compose-p8.py'
EXPECTED = '56f3ca480c31e2ffbf525ff4e3b77b354ecbb097088a9072c11372b03b5400a4'
ROOT = Path('/var/tmp/ga-e0t1.18-p10-compose-diagnostic-20260926')
MAIN_SHA = '5040c19623eddd137b48865e0406bfae2c57a2b7933780363c48fe124093f363'


def main():
    raw = BUILDER.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError('reviewed builder drift')
    if hashlib.sha256((HERE/'compose-main.go').read_bytes()).hexdigest() != MAIN_SHA:
        raise RuntimeError('candidate composition source drift')
    builder = types.ModuleType('reviewed_exact_builder'); builder.__file__ = str(BUILDER)
    exec(compile(raw, str(BUILDER), 'exec', dont_inherit=True), builder.__dict__)
    builder.ROOT = ROOT
    builder.HERE = HERE
    builder.main()


if __name__ == '__main__':
    main()
