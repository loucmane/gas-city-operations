"""gct-e8ex brief split: the reviewed r6 brief, verbatim, as a short task Bead and five closed spec holders.

  python3 -B split_e8ex.py render <out-dir> [<spec-1-id> ... <spec-5-id>]

Why: the Template `codex` worker reads its Bead with `/home/loucmane/gascity/bin/gc bd show <id>`, as its
prompt (gas-city-native agents/codex/prompt.template.md) names. For gct-e8ex that plain view is about 41K
characters (the 19.5K description and 6.5K of notes). Codex truncates long command output for the model, and
the first R3 attempt (ga-sh3w) already failed on an unreadable brief. The operator chose, on 2026-09-26, a
short task Bead plus closed spec holders with no edges; this applies it to the gct-e8ex brief, with every part
small enough that its plain view stays well under 10K.
- the task: the r6 head (title, role, Problem), the pointer, and the r6 tail (Out of scope, Acceptance);
- five closed holders: the candidate-lane section; the Goal up to the profile record; the profile record;
  the Goal from the renderer; the Tests.
Head + parts + tail reassemble byte for byte to the reviewed r6 brief (designs/step4-handover/gct-e8ex-brief.md
at 7bdae1ef, sha256 48c2cd87...), which is also the live gct-e8ex description. gct-e8ex stays open as the
umbrella; its notes (the coordinator activation checklist and review guidance) stay there.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

R6_COMMIT = '7bdae1eff1cc67aa660067c80748d6fe79712fb4'
R6_PATH = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/step4-handover/gct-e8ex-brief.md'
R6_SHA = '48c2cd873c27453fd9b82d75935e695d23626fda262c9141d5ddaeea57e55ffb'
OPS = '/home/loucmane/gas-city-ops'
GC_SHOW = '/home/loucmane/gascity/bin/gc bd show'
MARKERS = ('## The lane is a candidate lane', '## Goal', '- **A profile record**', '- **The renderer**', '## Tests',
           '## Out of scope')
TITLES = ('the candidate-lane section', 'the Goal, up to the profile record', 'the Goal, the profile record',
          'the Goal, from the renderer', 'the Tests')


def r6():
    raw = subprocess.run(['git', '--no-optional-locks', '-C', OPS, 'show', R6_COMMIT + ':' + R6_PATH],
                         check=True, capture_output=True).stdout
    assert hashlib.sha256(raw).hexdigest() == R6_SHA, 'r6 brief digest'
    return raw.decode()


def parts(full):
    cuts = []
    for marker in MARKERS:
        assert full.count(marker) == 1, marker
        cuts.append(full.index(marker))
    assert cuts == sorted(cuts)
    head, tail = full[:cuts[0]], full[cuts[-1]:]
    bodies = [full[a:b] for a, b in zip(cuts, cuts[1:])]
    assert head + ''.join(bodies) + tail == full
    return head, bodies, tail


def spec(n, body):
    return (f'gct-e8ex spec part {n} of 5 ({TITLES[n - 1]}). This Bead only holds text: it is not a work item and is\n'
            f'closed. The text below is verbatim from the reviewed r6 gct-e8ex brief (sha256 {R6_SHA[:16]}...);\n'
            f'parts 1 to 5 follow the task brief head in order.\n\n' + body)


def pointer(ids):
    lines = ['## The full specification (read first)\n\n',
             'This description continues in five spec Beads, split only because of its length. Their text is the rest of\n',
             'this description, verbatim from the reviewed r6 brief: the requirements this task must satisfy, incorporated\n',
             'here by reference. Before any work, read all five in full, in order, each as its own separate command:\n']
    for n, sid in enumerate(ids, 1):
        lines.append(f'{n}. `{GC_SHOW} {sid}` (part {n}: {TITLES[n - 1]});\n')
    lines.append('If any read is truncated or fails, stop: escalate to the mayor as your prompt describes, record which read\n'
                 'failed on this Bead, and do not guess the missing text.\n\n')
    return ''.join(lines)


def render(out, *ids):
    ids = ids or ('<spec-1>', '<spec-2>', '<spec-3>', '<spec-4>', '<spec-5>')
    assert len(ids) == 5
    full = r6()
    head, bodies, tail = parts(full)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    files = {f'spec-{n}.md': spec(n, body) for n, body in enumerate(bodies, 1)}
    files['task.md'] = head + pointer(ids) + tail
    for name, text in sorted(files.items()):
        (out / name).write_text(text)
        print(name, len(text.encode()), text.count('\n'), hashlib.sha256(text.encode()).hexdigest())
    return files


if __name__ == '__main__':
    assert sys.argv[1] == 'render'
    render(*sys.argv[2:])
