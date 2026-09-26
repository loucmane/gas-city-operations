"""Tests for the ga-e0t1.18 platform inspector rebinding. Read-only.

  python3 -m pytest -q designs/ga-e0t1.18-deploy/inspector/test_inspector.py
"""
import hashlib
import json
from pathlib import Path
import types

HERE = Path(__file__).parent
BUILD = Path('/var/tmp/ga-e0t1.18-platform-inspector-20260926')
LIVE = Path('/home/loucmane/gascity/city/.gc/platform/install-manifest.json')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_generator_reproduces_both_files():
    captured = {}
    make = types.ModuleType('make'); make.__file__ = str(HERE/'make_inspector.py')
    exec(compile((HERE/'make_inspector.py').read_bytes(), make.__file__, 'exec'), make.__dict__)
    make.write = lambda name, text: captured.__setitem__(name, text.encode())
    make.generate()
    assert set(captured) == {'platform-inspect-main.go', 'inspector-build.py'}
    for name, data in captured.items():
        assert (HERE/name).read_bytes() == data, name


def test_pin_is_the_live_m7_manifest():
    text = (HERE/'platform-inspect-main.go').read_text()
    assert 'const want = "%s"' % sha(LIVE) in text
    assert sha(LIVE) == '4bec5ef14bd81f6dc1830ada48fc502937ff91a531981dfff3fde5aaa92a9759'


def test_build_record_binds_the_sources():
    record = json.loads((BUILD/'build-result.json').read_bytes())
    assert record['core_commit'] == 'deefb98b2aed07875df31351d081fbac195cb1cd'
    assert record['core_tree'] == 'af5c3f045c1f50cd62c859f6dc58fa613e5f2f99'
    assert record['entrypoint_sha256'] == sha(HERE/'platform-inspect-main.go')
    assert record['builder_sha256'] == sha(HERE/'inspector-build.py')
    assert record['binary_sha256'] == sha(BUILD/'platform-inspect')
    assert record['executed'] is False and record['installed'] is False
