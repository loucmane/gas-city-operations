"""Compile the Template candidate policy and Preflight proof under pinned Core."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

from conftest import CoreBuildEnvironment
from test_managed_worker_canary_provisioning import (
    _reviewed_core_inputs,
    _run_core_interop_phases,
)
from test_operations_candidate_worker import _installed_paths, _provision
from test_template_candidate_worker import _template_candidate_prototype


ROOT = Path(__file__).resolve().parents[1]
CORE_TEST = ROOT / "tests/interop/core_template_candidate_preflight_test.go"


def test_template_candidate_receipt_policy_and_preflight_under_pinned_core(
    tmp_path: Path, core_build_environment: CoreBuildEnvironment
) -> None:
    core_source, core_commit = _reviewed_core_inputs()
    go = shutil.which("go")
    assert go is not None, "the pinned managed-worker Go toolchain is required"

    prototype = _template_candidate_prototype(tmp_path)
    provisioned = _provision(tmp_path, prototype, "--apply", "--json")
    assert provisioned.returncode == 0, provisioned.stderr
    _runner, receipt_path = _installed_paths(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    (profile,) = receipt["profiles"]

    unsafe_policy = tmp_path / "unsafe-template-policy.json"
    unsafe_policy.write_bytes(Path(profile["control_policy"]["path"]).read_bytes())
    unsafe_policy.chmod(0o664)

    archive = tmp_path / "reviewed-core.tar"
    archived = subprocess.run(
        [
            "/usr/bin/git",
            "-C",
            str(core_source),
            "archive",
            "--format=tar",
            f"--output={archive}",
            core_commit,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert archived.returncode == 0, archived.stderr
    core = tmp_path / "reviewed-core"
    core.mkdir()
    with tarfile.open(archive) as stream:
        stream.extractall(core, filter="data")

    synthetic = core / "internal/managedworker/template_candidate_preflight_external_test.go"
    overlay = tmp_path / "template-candidate-overlay.json"
    overlay.write_text(
        json.dumps({"Replace": {str(synthetic): str(CORE_TEST)}}), encoding="utf-8"
    )
    environment = core_build_environment.apply(os.environ)
    environment.update(
        {
            "GCT_TEMPLATE_RECEIPT": str(receipt_path),
            "GCT_TEMPLATE_PROFILE": profile["name"],
            "GCT_TEMPLATE_UNSAFE_POLICY": str(unsafe_policy),
        }
    )
    _run_core_interop_phases(
        go=go,
        core=core,
        overlay=overlay,
        environment=environment,
        evidence_dir=tmp_path / "template-candidate-core-interop",
    )
