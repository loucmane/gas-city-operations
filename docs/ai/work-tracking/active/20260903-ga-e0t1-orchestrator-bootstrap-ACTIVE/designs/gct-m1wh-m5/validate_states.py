"""Validate every composed city configuration state of the M5 prerequisite order.

Read-only with respect to the live city. Each state is composed in a fresh
shadow directory under <scratch>:
- city.toml and managed/rig-permissions.toml are candidate copies;
- `.gc` is a new directory holding only a copy of the site binding;
- every other city entry is a symlink.

Two checks run on every state.
- Installed `gc config show --validate` must accept every state. It is recorded
  as weak evidence, because it accepts even agent-level model values that are
  not offered. The unordered state (final city with the predecessor fragment)
  and a bogus model both pass it.
- prereqs.models is the semantic check: every claude-family selection must
  name an offered model. It must accept each state of the live order and refuse
  the unordered state.

Run it only before the live sequence starts. `gc config show` reads the pack
cache, so running it during the capture or the transaction window would break the
frozen cache closure.

  python3 -I -B validate_states.py <derive-out-dir> <scratch-dir>
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types

CITY = Path('/home/loucmane/gascity/city')
GC = '/home/loucmane/gascity/bin/gc'
ENV = {'PATH': '/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin', 'HOME': '/home/loucmane',
       'LANG': 'C', 'GC_HOME': '/home/loucmane/gascity/home'}


def shadow(root, city_toml, rig_toml):
    root.mkdir()
    for entry in sorted(os.listdir(CITY)):
        if entry in ('city.toml', 'managed', '.gc'):
            continue
        os.symlink(CITY / entry, root / entry)
    (root / 'city.toml').write_bytes(city_toml)
    (root / 'managed').mkdir()
    for entry in sorted(os.listdir(CITY / 'managed')):
        if entry != 'rig-permissions.toml':
            os.symlink(CITY / 'managed' / entry, root / 'managed' / entry)
    (root / 'managed/rig-permissions.toml').write_bytes(rig_toml)
    (root / '.gc').mkdir()
    shutil.copy2(CITY / '.gc/site.toml', root / '.gc/site.toml')


def validate(root):
    result = subprocess.run([GC, '--city', str(root), 'config', 'show', '--validate'], env=ENV, cwd='/',
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=120, check=False)
    return result.returncode, (result.stderr or result.stdout).decode(errors='replace').strip()[-400:]


def main():
    derived, scratch = Path(sys.argv[1]), Path(sys.argv[2])
    scratch.mkdir(exist_ok=False)
    old_city = (CITY / 'city.toml').read_bytes()
    old_rig = (CITY / 'managed/rig-permissions.toml').read_bytes()
    transition = (derived / 'city.toml.transition').read_bytes()
    final = (derived / 'city.toml.final').read_bytes()
    new_rig = (derived / 'rig-permissions.toml.new').read_bytes()
    source = Path(__file__).parent/'prereqs.py'
    prereqs = types.ModuleType('prereqs'); prereqs.__file__ = str(source)
    exec(compile(source.read_bytes(), str(source), 'exec', dont_inherit=True), prereqs.__dict__)
    states = [('predecessor', old_city, old_rig, True), ('after-city-transition', transition, old_rig, True),
              ('after-render', transition, new_rig, True), ('after-city-final', final, new_rig, True),
              ('unordered', final, old_rig, False)]
    report = []
    for name, city_toml, rig_toml, consistent in states:
        root = scratch / name
        shadow(root, city_toml, rig_toml)
        code, detail = validate(root)
        try:
            semantic = prereqs.models(city_toml.decode(), rig_toml.decode(), prereqs.fragment_texts())['selected']
            accepted = True
        except RuntimeError as exc:
            semantic, accepted = str(exc), False
        report.append(dict(state=name, gc_validate_returncode=code, semantic_accepted=accepted,
                           semantic=semantic, ok=code == 0 and accepted == consistent,
                           gc_detail=detail))
    print(json.dumps(report, indent=1))
    if not all(r['ok'] for r in report):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
