"""Offline binding proof, not live integrity or worker acceptance."""
import ast
import hashlib
import json
from pathlib import Path
import re
import types

import pytest

HERE = Path(__file__).parent
CORE_COMMIT = '53f2e232da03a1e176cf64cf4fe1aa9c3f3beb6b'
CORE_TREE = '2a253aabadc432c3c9f8953961b7a0db96291191'


def constants(path):
    values = {}
    for item in ast.parse(path.read_bytes()).body:
        if not isinstance(item, ast.Assign) or len(item.targets) != 1:
            continue
        key = item.targets[0]
        if not isinstance(key, ast.Name):
            continue
        value = item.value
        if isinstance(value, ast.Constant):
            values[key.id] = value.value
        elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'Path':
            values[key.id] = Path(ast.literal_eval(value.args[0]))
    return values


@pytest.mark.parametrize('name', ['observe-integrity-r11.py', 'observe-terminal-r11.py'])
def test_native_manifest_pin_matches_outer_observer(name):
    outer = constants(HERE / name)
    build = outer['BUILD']
    record = json.loads((build / 'build-result.json').read_bytes())
    entry = (build / 'source/cmd/ga-y49e-platform-inspect/main.go').read_bytes()
    assert hashlib.sha256(entry).hexdigest() == record['entrypoint_sha256']
    pins = re.findall(rb'const want = "([0-9a-f]{64})"', entry)
    assert pins == [outer['MANIFEST_SHA'].encode()]
    assert record['manifest_sha256'] == outer['MANIFEST_SHA']
    assert hashlib.sha256((build / 'platform-inspect').read_bytes()).hexdigest() == outer['BINARY_SHA']
    assert record['binary_sha256'] == outer['BINARY_SHA']


@pytest.mark.parametrize('name', ['observe-integrity-r11.py', 'observe-terminal-r11.py'])
def test_inspector_uses_the_adopted_core_source(name):
    outer = constants(HERE / name)
    record = json.loads((outer['BUILD'] / 'build-result.json').read_bytes())
    assert record['core_commit'] == CORE_COMMIT
    assert record['core_tree'] == CORE_TREE
    text = (HERE / name).read_text()
    assert CORE_COMMIT in text and CORE_TREE in text
    assert "result['manifest_sha256']==MANIFEST_SHA" in text


@pytest.mark.parametrize('suffix', ['build-result.json', 'platform-inspect', 'platform-inspect-main.go', 'inspector-build.py'])
def test_assembly_refuses_inspector_artifact_drift(monkeypatch, suffix):
    module = types.ModuleType('inspector_assembly')
    module.__file__ = str(HERE/'window-assembly.py')
    exec(compile((HERE/'window-assembly.py').read_bytes(), module.__file__, 'exec'), module.__dict__)
    original = Path.read_bytes

    def changed(path):
        raw = original(path)
        if path.name == suffix:
            return raw + b'\nDRIFT\n'
        return raw

    monkeypatch.setattr(Path, 'read_bytes', changed)
    with pytest.raises(ValueError, match='inspector .* drift'):
        module.bind_inspector({})


def test_failed_inspection_archive_contract_is_exact_and_does_not_retry():
    text = (HERE/'preserve-inspector-refusal.py').read_text()
    ast.parse(text)
    assert "JOB_COMMITS={'ga-mb91-observe-r2':'99470070947b50a10a7a89f8e816043af332af7b'}" in text
    assert 'EXPECTED_EXIT=1' in text
    assert "done['unit_state_after']=='inactive'" in text
    assert 'submit_job' not in text and 'systemd-run' not in text
    assert "assert set(p.name for p in failed.iterdir())==set(expected)" in text
    record = json.loads((HERE/'INSPECTOR-REFUSAL-R2.json').read_bytes())
    for name, item in record['files'].items():
        assert name in text and item['sha256'] in text
    assert record['phase']['stderr'] == 'manifest bytes drift\n'
    assert record['phase']['cleanup']['owned_process_group_gone'] is True
    assert record['phase']['cleanup']['unexpected_survivors'] is False
