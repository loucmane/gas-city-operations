"""Pure source assembly from the consumed R5 probe; no execution or live writes."""
import ast
import hashlib
from pathlib import Path

import build

R5 = 'ff1212c23576ff3f2da13ba4ddf703c18ce9bc68'
PROBE_SHA = '1766846356f763e1b98ed6276b916e53daf7493786e4f73fb7f6648146ab1f67'


def worker_probe():
    before = build.git('show', R5 + ':' + build.NEW + '/worker-startup.py')
    assert hashlib.sha256(before).hexdigest() == PROBE_SHA, 'consumed R5 probe drift'
    helper = (Path(__file__).parent/'auth_status_r6.py').read_text()
    helper_tree = ast.parse(helper)
    # Embed only the exact reviewed constants and function. Existing hashlib
    # import remains the sole dependency; no new worker read grant is needed.
    nodes = helper_tree.body[2:]
    assert [type(n).__name__ for n in nodes] == ['Assign', 'Assign', 'FunctionDef']
    assert nodes[-1].name == 'subscription_status'
    addition = '\n\n'.join(ast.get_source_segment(helper, node) for node in nodes) + '\n\n\n'
    text = build.once(before.decode(), 'def main(session_id):\n', addition + 'def main(session_id):\n')
    old = "    lines = (auth.stdout + auth.stderr).decode('utf-8', 'strict').strip()\n" \
          "    require(auth.returncode == 0 and lines == 'Logged in using ChatGPT', 'subscription identity unproven')"
    text = build.once(text, old, '    subscription_status(auth.returncode, auth.stdout, auth.stderr)')
    ast.parse(text)
    return before, text.encode()
