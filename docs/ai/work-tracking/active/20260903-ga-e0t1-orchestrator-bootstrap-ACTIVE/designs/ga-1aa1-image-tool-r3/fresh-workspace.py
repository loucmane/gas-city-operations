"""Fresh workspace admission before Core materializes runtime files.

Git head/status and the common-Git snapshot are independently checked by the
window. No old startup file or Core-materialized hook is grandfathered in.
The hook is verified after actual startup before the source-release decision.
"""
import stat

PINS = {
    'image_tool.py': 'd0c606f15e12d6b45e31c7c8d2dead612133ad8e17340d98747080888468bc9d',
    'test_image_tool.py': 'da078e721ddbd7e66a0adcc02a8eca64658e2bab92a62ce24b9fe810b0ada992',
    'pins.json': '84b0180f019bbf1441941308c7a299f53c38a311fd5e5620122fd9f51466158f',
    'make_pins.py': '5586f7aa8a20a7a2e24c16f36b7c66e4324089854fd4e379987a0a67544f486a',
}


def verify(w, current, runtime):
    c = w.contract()
    w.require(isinstance(current, dict) and current, 'empty fresh workspace image')
    for path, record in runtime.items():
        if record['type'] != stat.S_IFDIR:
            w.require(path not in current, 'fresh workspace already has runtime materialization')
    w.require(not any(path == '.gc/worker-evidence' or path.startswith('.gc/worker-evidence/')
                      for path in current), 'fresh workspace already has worker evidence')
    for name, digest in PINS.items():
        path = c.SCOPE_ROOT + name
        row = current.get(path)
        w.require(isinstance(row, dict) and row.get('type') == stat.S_IFREG
                  and row.get('sha256') == digest and row.get('mode') == 0o644,
                  'fresh source or preserved image pin differs')
    for path, digest in c.RULES.items():
        row = current.get(path)
        w.require(isinstance(row, dict) and row.get('type') == stat.S_IFREG
                  and row.get('sha256') == digest and row.get('mode') == 0o644,
                  'fresh local policy differs')
    return current
