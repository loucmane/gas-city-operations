"""Create the sequence 15 broker envelope for the CURRENT attempt, never overwriting one (ga-e0t1.18 S2 r5).

  python3 -I -B make_envelope.py

The installed broker's `prepare` writes its output with an atomic replace, so running it with a stale output path
would silently overwrite a preserved envelope that an earlier attempt's envelope-binding.json still names (S2 r4
review B). This wrapper removes the choice:
- ROOT is read from the committed s2_transition.py (the current attempt, including any -tN retry suffix);
- it refuses unless ROOT/preflight.json exists (prepare has run) and ROOT/envelope.json does not;
- it runs the broker's prepare with the fixed operation, artifact, bead, source and sequence, and nothing else;
- it prints the envelope's sha256 for bind-envelope.
"""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BROKER = '/usr/local/libexec/gas-city/gct-privileged-provision'
ARGS = ['--operation', 'replace-gas-city-control-plane.v1',
        '--artifact', '/var/tmp/ga-e0t1.18-build-20260926/gc-a',
        '--bead', 'ga-ecwh',
        '--commit', 'deefb98b2aed07875df31351d081fbac195cb1cd',
        '--tree', 'af5c3f045c1f50cd62c859f6dc58fa613e5f2f99',
        '--sequence', '15']


def current_root(transition=HERE/'s2_transition.py'):
    [root] = re.findall(r"^ROOT=Path\('(/var/tmp/ga-e0t1\.18-seq15-20260926(?:-t[0-9]+)?)'\)$",
                        transition.read_text(), re.M)
    return Path(root)


def command(root):
    return [BROKER, 'prepare', *ARGS, '--output', str(root/'envelope.json')]


def preconditions(root):
    if not (root/'preflight.json').is_file():
        raise SystemExit('refused: %s has no preflight.json; run prepare first' % root)
    if os.path.lexists(root/'envelope.json'):
        raise SystemExit('refused: %s/envelope.json already exists; never overwrite an envelope' % root)


def main():
    if not (sys.flags.isolated and sys.flags.dont_write_bytecode):
        raise SystemExit('use python3 -I -B')
    root = current_root()
    preconditions(root)
    subprocess.run(command(root), check=True, stdin=subprocess.DEVNULL, timeout=90)
    print(hashlib.sha256((root/'envelope.json').read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
