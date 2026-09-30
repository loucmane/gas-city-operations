"""Replay the frozen R12 regression corpus against R13 via explicit aliases."""
from pathlib import Path
import sys
import types

HERE = Path(__file__).parent
for name in ('release_delivery_r12', 'release_runtime_r12'):
    path = HERE / (name.replace('_', '-').replace('r12', 'r13') + '.py')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    sys.modules[name] = module
