"""Read-only inventory of every link and skill ownership manifest that embeds the live bundled cache key.

The roots are the city and every rig it registers, the same five that the reviewed ga-nibd window's
restore-r9-routes-r3.py enumerates. For each root it records:
- every symlink whose target contains the live key a21cc0a2, with its target;
- every .gc-skill-ownership.json that contains the key, with its sha, its size and its
  post-substitution sha.
It also proves that every key-bearing manifest entry names a link that exists in that sink with the
same target. Without that, a stale entry would not be substituted, and the exact-bytes expectation
would be wrong. Nothing is written except the two TSV outputs next to this file.
"""
import hashlib
import json
import os
from pathlib import Path

LIVE = 'a21cc0a2fbf22c14fbe59cf508d05bcc230774f5c0d9cd386215369d43a2410a'
NEW = '69fe9a2e6239743677a6e13188096df34d6eb6d41fad171af58671ef288fdd3f'
ROOTS = ['/home/loucmane/gascity/city', '/home/loucmane/gas-city-native',
         '/home/loucmane/gascity/city/rigs/gascity', '/home/loucmane/dev/blog',
         '/home/loucmane/dev/hpfetcher-gc-main']
HERE = Path(__file__).parent
MAX_DEPTH = 4


def walk(root):
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        if depth >= MAX_DEPTH:
            dirnames[:] = []
        dirnames[:] = [d for d in dirnames if d not in ('.git', 'node_modules') and
                       not os.path.islink(os.path.join(dirpath, d))]
        for name in filenames + [d for d in os.listdir(dirpath) if os.path.islink(os.path.join(dirpath, d))]:
            yield Path(dirpath) / name


def main():
    links, manifests, seen = [], [], set()
    for root in ROOTS:
        for path in walk(root):
            if str(path) in seen:
                continue
            seen.add(str(path))
            if path.is_symlink():
                target = os.readlink(path)
                if LIVE in target:
                    links.append((str(path), target))
            elif path.name == '.gc-skill-ownership.json' and path.is_file():
                data = path.read_bytes()
                if LIVE.encode() not in data:
                    continue
                entries = json.loads(data)['targets']
                for name, target in entries.items():
                    if LIVE in target:
                        link = path.parent / name
                        assert link.is_symlink() and os.readlink(link) == target, (str(link), target)
                new = data.replace(LIVE.encode(), NEW.encode())
                manifests.append((str(path), hashlib.sha256(data).hexdigest(), len(data),
                                  hashlib.sha256(new).hexdigest()))
    links.sort()
    manifests.sort()
    (HERE / 'live-key-links.tsv').write_text(''.join(f'{p}\t{t}\n' for p, t in links))
    (HERE / 'live-key-manifests.tsv').write_text(
        ''.join(f'{p}\t{s}\t{n}\t{e}\n' for p, s, n, e in manifests))
    per_root = {r: sum(1 for p, _ in links if p.startswith(r + '/') and
                       not any(p.startswith(o + '/') for o in ROOTS if o != r and o.startswith(r + '/')))
                for r in ROOTS}
    print(json.dumps({'links': len(links), 'manifests': len(manifests), 'per_root': per_root}, indent=1))


if __name__ == '__main__':
    main()
