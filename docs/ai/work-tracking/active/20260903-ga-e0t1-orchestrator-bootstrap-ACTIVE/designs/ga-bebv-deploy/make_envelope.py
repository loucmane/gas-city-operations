"""Create the sequence 16 broker envelope for the CURRENT attempt, never overwriting one (ga-e0t1.18 S2 r5).

  python3 -I -B make_envelope.py

The installed broker's `prepare` writes its output with an atomic replace, so running it with a stale output path
would silently overwrite a preserved envelope that an earlier attempt's envelope-binding.json still names (S2 r4
review B). This wrapper removes the choice:
- ROOT is read from s2_transition.py beside it (test_s2.py ties that file to the generator output), including any
  -tN retry suffix;
- it holds ROOT/execution.lock, the lock every phase takes, for the whole run (s2 r6);
- it refuses unless prepare completed (preflight.json and prepare-done.json), the attempt is not terminal, and
  ROOT/envelope.json does not exist, and it checks the installed broker's pin (s2 r6);
- it runs the broker's prepare with the fixed operation, artifact, bead, source and sequence, and nothing else;
- it prints the envelope's sha256 for bind-envelope.
"""
import fcntl
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BROKER = '/usr/local/libexec/gas-city/gct-privileged-provision'
ARGS = ['--operation', 'replace-gas-city-control-plane.v1',
        '--artifact', '/var/tmp/ga-bebv-build-20260927/gc-a',
        '--bead', 'ga-ecwh',
        '--commit', 'f45a626213dc5b8d0b52f097d978cca56e506df0',
        '--tree', 'f1011adaf673937fbda1d254a53c8f0eadf17c5c',
        '--sequence', '16']


def current_root(transition=HERE/'s2_transition.py'):
    [root] = re.findall(r"^ROOT=Path\('(/var/tmp/ga-bebv-seq16-20260927(?:-t[0-9]+)?)'\)$",
                        transition.read_text(), re.M)
    return Path(root)


def command(root):
    return [BROKER, 'prepare', *ARGS, '--output', str(root/'envelope.json')]


BROKER_PIN = dict(sha256='0f56141d190c72474e9c74db0dd8d1c04789b089279721f3140cf727675615d5', uid=0, gid=0,
                  mode=0o755, size=60424)  # the pin s2_transition.py submit() checks


def preconditions(root):
    if not (root/'preflight.json').is_file() or not (root/'prepare-done.json').is_file():
        raise SystemExit('refused: %s has no completed prepare (preflight.json, prepare-done.json); run prepare first' % root)
    if os.path.lexists(root/'terminal.json'):
        raise SystemExit('refused: %s is terminal; never sign an envelope for a dead attempt' % root)
    if os.path.lexists(root/'envelope.json'):
        raise SystemExit('refused: %s/envelope.json already exists; never overwrite an envelope' % root)


def broker_pin(path=BROKER):
    st = os.stat(path, follow_symlinks=False)
    with open(path, 'rb') as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    actual = dict(sha256=digest, uid=st.st_uid, gid=st.st_gid, mode=st.st_mode & 0o7777, size=st.st_size)
    if actual != BROKER_PIN:
        raise SystemExit('refused: installed broker pin drift %r' % actual)


def main():
    if not (sys.flags.isolated and sys.flags.dont_write_bytecode):
        raise SystemExit('use python3 -I -B')
    root = current_root()
    # s2 r6: hold the attempt's execution lock (the one every s2_transition.py phase takes) across the checks and
    # the broker call, so no phase and no second wrapper can run in between.
    fd = os.open(root/'execution.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        preconditions(root)
        broker_pin()
        subprocess.run(command(root), check=True, stdin=subprocess.DEVNULL, timeout=90)
        print(hashlib.sha256((root/'envelope.json').read_bytes()).hexdigest())
    finally:
        os.close(fd)


if __name__ == '__main__':
    main()
