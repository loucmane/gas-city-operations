"""Load only the two local source candidates, without bytecode writes."""
from pathlib import Path
import sys
import types

HERE = Path(__file__).parent
for name in ('release_delivery_r12', 'release_runtime_r12'):
    path = HERE / (name.replace('_', '-') + '.py')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    sys.modules[name] = module
