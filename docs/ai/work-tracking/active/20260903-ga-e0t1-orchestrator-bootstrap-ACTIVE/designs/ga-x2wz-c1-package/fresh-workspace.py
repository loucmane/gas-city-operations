"""Fresh workspace admission before Core materializes runtime files.

Git head/status and the common-Git snapshot are independently checked by the
window. No old startup file or Core-materialized hook is grandfathered in.
The hook is verified after actual startup before the source-release decision.
"""
import stat

PINS = {
    "docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-handover/image/image_tool.py": "ac449526353cd78214da68c5acdc2394b33217de263fb1a468f1c35405281b60",
    "docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-handover/image/test_image_tool.py": "b49888bdf0ef2de13207e200cd063ca6a80910587ef61d532f83abbd737b31d3",
    "docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-handover/image/pins.json": "84b0180f019bbf1441941308c7a299f53c38a311fd5e5620122fd9f51466158f",
    "docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-handover/image/make_pins.py": "5586f7aa8a20a7a2e24c16f36b7c66e4324089854fd4e379987a0a67544f486a",
    "docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/DESIGN.md": "afda2b61f57fa3700433e727b4a19a079c5d5ae2d2c44aa7d5a745790a9610bd",
    "docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/HANDOVER.md": "5427b55997b84e6b672f80c8df6328cf6929abf00a6999b67363b2b79d79a73a",
    "docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/slots/slots.py": "4aefce14a0cae55bc3242ad586f3383450ae84e6dade3522d297ede5f2aae5ab",
    "docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/slots/test_slots.py": "bbf2add8547d557c7ce22435b375fc17cfe27f0c5c58a3493ba7cc034dc0cf29"
}


def verify(w, current, runtime):
    c = w.contract()
    w.require(isinstance(current, dict) and current, 'empty fresh workspace image')
    for path, record in runtime.items():
        if record['type'] != stat.S_IFDIR:
            w.require(path not in current, 'fresh workspace already has runtime materialization')
    w.require(not any(path == '.gc/worker-evidence' or path.startswith('.gc/worker-evidence/')
                      for path in current), 'fresh workspace already has worker evidence')
    w.require(not any(path in current for path in c.SOURCE_PATHS), 'new product path already exists')
    for path, digest in PINS.items():
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
