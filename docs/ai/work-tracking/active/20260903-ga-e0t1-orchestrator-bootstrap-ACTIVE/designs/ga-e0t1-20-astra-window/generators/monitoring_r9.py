"""Offline exact transformation of the reviewed R8 release checks."""
import ast
from pathlib import Path

import build

HERE = Path(__file__).parent
NOW = "datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','').rstrip('0').rstrip('.')+'Z'"


def sources(validator, release):
    helper = (HERE/'review_wait_r9.py').read_text()
    selected = [node for node in ast.parse(helper).body
                if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign))
                or isinstance(node, ast.FunctionDef) and node.name in ('stamp', 'monitoring_state', 'waiting_turn')]
    # Retain the original require function and all other original validators.
    appendix = '\n\n'.join(ast.get_source_segment(helper, node) for node in selected)
    old = "    require(task.get('metadata') == expected, 'claim metadata differs')"
    new = ("    if 'started_at' in routed:\n"
           "        monitoring_state(task,routed,session," + NOW + ")\n"
           "    else:\n" + '    ' + old)
    validator = build.once(validator.decode(), old, new) + '\n\n' + appendix + '\n'
    release = build.once(release.decode(), 'import hashlib\n',
                         'from datetime import datetime, timezone\nimport hashlib\n')
    release = build.once(release, '    v.live_task(task,routed,s,w.contract(),sha)\n',
        '    v.live_task(task,routed,s,w.contract(),sha)\n'
        '    monitoring=v.monitoring_state(task,routed,s,' + NOW + ')\n'
        "    waiting_raw=inspector.file_bytes(Path(proof['transcript_path']),32<<20)\n"
        "    require(hashlib.sha256(waiting_raw).hexdigest()==proof['native']['rollout_sha256'],'native transcript changed during initial proof')\n"
        '    waiting=v.waiting_turn(waiting_raw,s,sha,PROBE_SHA,' + NOW + ')\n')
    release = build.once(release,
        '        workspace_pristine=True,client_inputs=client_after,common_git_unchanged=True))',
        '        workspace_pristine=True,client_inputs=client_after,common_git_unchanged=True,\n'
        '        monitoring_adjudication=monitoring,waiting_turn=waiting))')
    release = build.once(release, "    require(task2==task,'claim or task changed before release')",
        '    v.live_task(task2,routed,s2,w.contract(),sha)\n'
        "    require(task2==task,'claim or task changed before release')\n"
        "    require(inspector.file_bytes(Path(proof['transcript_path']),32<<20)==waiting_raw,'native waiting transcript changed before release')")
    ast.parse(validator)
    ast.parse(release)
    return validator.encode(), release.encode()
