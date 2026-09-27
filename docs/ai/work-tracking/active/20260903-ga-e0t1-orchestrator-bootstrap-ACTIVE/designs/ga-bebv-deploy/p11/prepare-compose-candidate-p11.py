"""P11 candidate composition diagnostic: the P11 exact-source builder, unchanged, into a fresh root.

Only the root and the composition source directory change. candidate/compose-main.go is the P10 candidate
composition source (5040c196), byte for byte. The builder records the Core commit, tree, archive, Go executable
and the source digest in build-result.json.
"""
import hashlib
from pathlib import Path
import types

HERE = Path(__file__).parent
BUILDER = HERE/'prepare-compose-p11.py'
EXPECTED = 'ba9be1f66c6a49060f73aa885e2c1c84ddb913a0985b0b5bca8bf52368560130'
ROOT = Path('/var/tmp/ga-bebv-p11-candidate-compose-diagnostic-20260927')
MAIN_SHA = '5040c19623eddd137b48865e0406bfae2c57a2b7933780363c48fe124093f363'


def main():
    raw = BUILDER.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError('reviewed builder drift')
    if hashlib.sha256((HERE/'candidate'/'compose-main.go').read_bytes()).hexdigest() != MAIN_SHA:
        raise RuntimeError('candidate composition source drift')
    builder = types.ModuleType('reviewed_exact_builder'); builder.__file__ = str(BUILDER)
    exec(compile(raw, str(BUILDER), 'exec', dont_inherit=True), builder.__dict__)
    builder.ROOT = ROOT
    builder.HERE = HERE/'candidate'
    builder.main()


if __name__ == '__main__':
    main()
