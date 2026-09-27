"""P12 Template candidate composition diagnostic: the reviewed P11 exact-source builder, in place, into a fresh root.

The builder is loaded from ga-bebv-deploy/p11 by digest and runs unchanged, so build-result.json records the same
builder_sha256 as the P11 signing and Operations candidate diagnostics. Only the root and the composition source
directory change. template/compose-main.go is the P11 candidate composition source (5040c196) with the target
identity and the provider name substituted (make_p12.py).
"""
import hashlib
from pathlib import Path
import types

HERE = Path(__file__).parent
BUILDER = HERE.parent.parent/'ga-bebv-deploy'/'p11'/'prepare-compose-p11.py'
EXPECTED = 'ba9be1f66c6a49060f73aa885e2c1c84ddb913a0985b0b5bca8bf52368560130'
ROOT = Path('/var/tmp/gct-oak5-p12-template-compose-diagnostic-20260927')
MAIN_SHA = '472abbee0d560e092f4cf3c062cb47c0f04cd7010df8e28a871ff40b61d2a233'


def main():
    raw = BUILDER.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError('reviewed builder drift')
    if hashlib.sha256((HERE/'template'/'compose-main.go').read_bytes()).hexdigest() != MAIN_SHA:
        raise RuntimeError('Template composition source drift')
    builder = types.ModuleType('reviewed_exact_builder'); builder.__file__ = str(BUILDER)
    exec(compile(raw, str(BUILDER), 'exec', dont_inherit=True), builder.__dict__)
    builder.ROOT = ROOT
    builder.HERE = HERE/'template'
    builder.main()


if __name__ == '__main__':
    main()
