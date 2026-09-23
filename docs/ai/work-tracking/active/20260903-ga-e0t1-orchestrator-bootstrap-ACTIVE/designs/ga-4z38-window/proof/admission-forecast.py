"""Read-only forecast of the round-2a base admission, minus the host block (needs supervisor namespaces).

Loads the generated window-base-r11.py, runs pins() and the snapshot() comparison pieces with the real
observer, and reports every difference between the live image and approved_historical_image(P6).
"""
import hashlib
import json
import sys
import types
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent


def diff(a, z, path=''):
    if isinstance(a, dict) and isinstance(z, dict):
        for k in sorted(set(a) | set(z)):
            if k not in a or k not in z:
                yield path + '/' + k, a.get(k, '<absent>'), z.get(k, '<absent>')
            else:
                yield from diff(a[k], z[k], path + '/' + k)
    elif a != z:
        yield path, a, z


def main():
    raw = (PKG/'window-base-r11.py').read_bytes()
    w = types.ModuleType('forecast_base')
    w.__file__ = str(PKG/'window-base-r11.py')
    exec(compile(raw, w.__file__, 'exec', dont_inherit=True), w.__dict__)
    b, o, owned = w.load_support()
    w.pins()
    prior = json.loads(w.read(w.ACCEPTED, w.ACCEPTED_SHA))
    files = {path: o.read_file(path)[0] for path in prior['pins']}
    value = dict(host=prior['host'], pins=files, cache=o.tree_snapshot(b.CACHE, cache=True),
                 protected={str(p): o.tree_snapshot(p, protected=True) for p in b.PROTECTED})
    expected = w.dependency_image(w.approved_historical_image(prior))
    observed = w.dependency_image(value)
    differences = list(diff(expected, observed))
    providers = w.provider_pins(b, o)
    accepted_provider = json.loads(w.read(Path(str(w.ACCEPTED) + '.provider-pins'), w.PROVIDER_SHA))
    provider_diff = list(diff(w.dependency_image(accepted_provider), w.dependency_image(providers)))
    print(json.dumps(dict(base_sha256=hashlib.sha256(raw).hexdigest(), admission_equal=not differences,
                          differences=[[p, str(a)[:200], str(z)[:200]] for p, a, z in differences[:40]],
                          difference_count=len(differences), providers_equal=not provider_diff,
                          provider_differences=[[p, str(a)[:200], str(z)[:200]] for p, a, z in provider_diff[:20]]),
                     indent=1))
    return 0 if not differences and not provider_diff else 1


if __name__ == '__main__':
    sys.exit(main())
