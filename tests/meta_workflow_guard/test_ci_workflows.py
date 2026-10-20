"""Regression tests for GitHub Actions CI workflow contracts."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CODEX_GUARD_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "codex-guard.yml"
META_GUARD_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "meta-workflow-guard.yml"
WITNESS_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "aegis-witness.yml"
DELIVERY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "aegis-autonomous-delivery.yml"
DEPENDENCY_REVIEW_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "dependency-review.yml"
DEPENDABOT_CONFIG = REPO_ROOT / ".github" / "dependabot.yml"
TASKMASTER_COMPATIBILITY_SCRIPT = REPO_ROOT / "scripts" / "aegis-ci-taskmaster-compatibility"
WORKFLOW_PATHS = (
    CI_WORKFLOW,
    CODEX_GUARD_WORKFLOW,
    META_GUARD_WORKFLOW,
    WITNESS_WORKFLOW,
    DELIVERY_WORKFLOW,
    DEPENDENCY_REVIEW_WORKFLOW,
)

ACTION_PINS = {
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",  # v7.0.1
    "actions/setup-python": "ece7cb06caefa5fff74198d8649806c4678c61a1",  # v6.0.0
    "actions/setup-node": "249970729cb0ef3589644e2896645e5dc5ba9c38",  # v6.0.0
    "actions/upload-artifact": "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",  # v7.0.0
    "astral-sh/setup-uv": "20cfd1bf945f4377ade1205e4dbc17946fc9a30d",  # v10.0.1
    "actions/dependency-review-action": "a1d282b36b6f3519aa1f3fc636f609c47dddb294",  # v5.0.0
}


def _load_workflow() -> dict:
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))


def _load_workflow_path(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_python_test_workflow_has_version_matrix() -> None:
    workflow = _load_workflow()
    matrix = workflow["jobs"]["python-tests"]["strategy"]["matrix"]

    assert matrix["python-version"] == ["3.11", "3.12", "3.13", "3.14"]
    assert workflow["jobs"]["python-tests"]["strategy"]["fail-fast"] is False


def test_all_external_actions_are_immutable_full_sha_pins() -> None:
    for path in WORKFLOW_PATHS:
        workflow = _load_workflow_path(path)
        text = path.read_text(encoding="utf-8")

        assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24" not in workflow.get("env", {})
        assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24" not in text
        uses = re.findall(r"^\s*uses:\s+([^\s#]+)", text, flags=re.MULTILINE)
        assert uses, path
        for reference in uses:
            if reference.startswith("./"):
                continue
            action, separator, revision = reference.partition("@")
            assert separator == "@", (path, reference)
            assert re.fullmatch(r"[0-9a-f]{40}", revision), (path, reference)
            assert ACTION_PINS[action] == revision, (path, reference)

    ci_workflow = _load_workflow()
    steps = ci_workflow["jobs"]["legacy-taskmaster-compatibility"]["steps"]
    taskmaster_node_step = next(step for step in steps if step.get("name") == "Set up Node for Taskmaster CLI")
    assert taskmaster_node_step["uses"] == (
        "actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38"
    )
    assert taskmaster_node_step["with"]["node-version"] == "22"


def test_python_test_workflow_runs_full_pytest_without_taskmaster_provisioning() -> None:
    workflow = _load_workflow()
    steps = workflow["jobs"]["python-tests"]["steps"]
    text = "\n".join(str(step) for step in steps)

    assert "uv run --frozen --no-sync python -m pytest" in text
    assert "scripts/template-ssot-scanner" not in text, "pytest config should own test discovery"
    assert "task-master" not in text
    assert "taskmaster health" not in text


def test_python_test_workflow_uses_the_committed_uv_lock_without_floating_installs() -> None:
    text = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d" in text
    assert 'version: "0.12.6"' in text
    assert "uv sync --locked --all-groups" in text
    assert "uv run --frozen --no-sync" in text
    assert "pip install" not in text
    assert "/tmp/codex-ci-dependencies.txt" not in text


def test_taskmaster_is_a_conditional_legacy_compatibility_job() -> None:
    workflow = _load_workflow()
    classify = workflow["jobs"]["classify-compatibility"]
    compatibility = workflow["jobs"]["legacy-taskmaster-compatibility"]
    steps = compatibility["steps"]
    step_names = [step.get("name") for step in steps]
    text = CI_WORKFLOW.read_text(encoding="utf-8")

    assert classify["outputs"] == {
        "taskmaster": "${{ steps.scope.outputs.taskmaster }}",
    }
    assert compatibility["needs"] == "classify-compatibility"
    assert compatibility["if"] == "needs.classify-compatibility.outputs.taskmaster == 'true'"
    assert ".taskmaster/**" in text
    assert "taskmaster-toolchain.json" in text
    assert "aegis_foundation/taskmaster_toolchain.py" in text
    assert "Set up Node for Taskmaster CLI" in step_names
    assert "Provision pinned Taskmaster CLI" in step_names
    assert "Run Taskmaster health" in step_names
    assert "Run legacy Taskmaster compatibility tests" in step_names
    assert step_names.index("Provision pinned Taskmaster CLI") < step_names.index(
        "Run legacy Taskmaster compatibility tests"
    )
    assert "python -m aegis_foundation.taskmaster_toolchain install-spec" in text
    assert 'npm install -g "$TASKMASTER_INSTALL_SPEC"' in text
    assert "python scripts/codex-task taskmaster health" in text


def test_python_test_workflow_captures_shadow_cascade_validation_artifact() -> None:
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    script = TASKMASTER_COMPATIBILITY_SCRIPT.read_text(encoding="utf-8")

    assert "Capture reconcile shadow cascade validation" in text
    assert "build_ci_shadow_cascade_validation_report" in script
    assert "capture_taskmaster_toolchain_evidence" in script
    assert "reconcile-shadow-cascade-validation.json" in script
    assert "task-master set-status" not in text
    assert "--apply" not in text


def test_python_test_workflow_captures_shadow_accumulation_with_side_effect_oracle() -> None:
    workflow = _load_workflow()
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    script = TASKMASTER_COMPATIBILITY_SCRIPT.read_text(encoding="utf-8")
    steps = workflow["jobs"]["legacy-taskmaster-compatibility"]["steps"]
    step_names = [step.get("name") for step in steps]

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["python-tests"]["permissions"] == {"contents": "read"}
    assert all(
        job.get("permissions", {"contents": "read"}).get("contents") != "write"
        for job in workflow["jobs"].values()
    )
    assert "Capture post-merge reconcile shadow accumulation" in step_names
    assert "build_shadow_accumulation_report" in script
    assert "classify_shadow_accumulation_evidence" in script
    assert (
        'payload["evidence_classification"] = classify_shadow_accumulation_evidence(payload)'
        in script
    )
    assert "reconcile-shadow-accumulation.json" in script
    assert "snapshot_whole_tree(repo, require_tmp_root=False)" in script
    assert "before.assert_matches" in script
    assert 'runner_temp_raw = os.environ.get("RUNNER_TEMP", "").strip()' in script
    assert "before.assert_matches(snapshot_whole_tree(repo, require_tmp_root=False))" in script
    assert '"valid_for_shadow": context["valid_for_shadow"]' in script
    assert "if context[\"valid_for_shadow\"]:" in script
    assert "reports/ci/" in text
    assert "${{ runner.temp }}/aegis-shadow/" in text
    assert "task-master set-status" not in text
    assert "--apply" not in text


def test_python_test_workflow_captures_shadow_precision_corpus_artifact() -> None:
    workflow = _load_workflow()
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    script = TASKMASTER_COMPATIBILITY_SCRIPT.read_text(encoding="utf-8")
    compact_script = "".join(script.split())
    steps = workflow["jobs"]["legacy-taskmaster-compatibility"]["steps"]
    step_names = [step.get("name") for step in steps]

    assert "Capture reconcile shadow precision corpus" in step_names
    assert "build_replayable_shadow_precision_corpus_artifact" in script
    assert "reconcile_shadow_precision_corpus.json" in script
    assert "reconcile-shadow-precision-corpus.json" in script
    assert "snapshot_whole_tree(repo, require_tmp_root=False)" in script
    assert "before.assert_matches(snapshot_whole_tree(repo, require_tmp_root=False))" in script
    assert 'if not payload["precision_gate"]["passed"]' in script
    assert "build_validated_taskmaster_ci_toolchain_baseline" in script
    assert "capture_taskmaster_toolchain_evidence" in script
    assert (
        "validated_toolchain_evidence="
        "build_validated_taskmaster_ci_toolchain_baseline(os.environ)"
        in compact_script
    )
    assert (
        "current_toolchain_evidence="
        "capture_taskmaster_toolchain_evidence(os.environ)"
        in compact_script
    )
    assert (
        "validated_toolchain_evidence="
        "capture_taskmaster_toolchain_evidence(os.environ)"
        not in compact_script
    )
    assert (
        '"tests"/"fixtures"/"aegis"/"reconcile_shadow_precision_corpus.json"'
        in compact_script
    )
    assert "${{ runner.temp }}/aegis-shadow/" in text
    assert "task-master set-status" not in text
    assert "--apply" not in text


def test_python_test_workflow_uploads_matrix_artifacts() -> None:
    workflow = _load_workflow()
    steps = workflow["jobs"]["python-tests"]["steps"]
    upload_step = next(step for step in steps if step.get("name") == "Upload pytest artifacts")

    assert upload_step["uses"] == (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    )
    assert "reports/ci/" in CI_WORKFLOW.read_text(encoding="utf-8")
    assert "${{ runner.temp }}/aegis-shadow/" in CI_WORKFLOW.read_text(encoding="utf-8")


def test_python_test_workflow_pins_shadow_artifact_upload_roots() -> None:
    workflow = _load_workflow()
    steps = workflow["jobs"]["python-tests"]["steps"]
    upload_step = next(step for step in steps if step.get("name") == "Upload pytest artifacts")
    upload_paths = [
        line.strip()
        for line in str(upload_step["with"]["path"]).splitlines()
        if line.strip()
    ]

    assert upload_step["uses"] == (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    )
    assert upload_paths == [
        "reports/ci/",
    ]


def test_workflows_are_least_privilege_bounded_and_cancel_stale_pr_runs() -> None:
    for path in (CI_WORKFLOW, CODEX_GUARD_WORKFLOW, META_GUARD_WORKFLOW, WITNESS_WORKFLOW):
        workflow = _load_workflow_path(path)
        assert workflow["permissions"] == {"contents": "read"}, path
        assert workflow["concurrency"]["cancel-in-progress"] == (
            "${{ github.event_name == 'pull_request' }}"
        ), path
        for job in workflow["jobs"].values():
            assert isinstance(job.get("timeout-minutes"), int), (path, job)
            assert job["timeout-minutes"] <= 30, (path, job)

    codex = _load_workflow_path(CODEX_GUARD_WORKFLOW)
    assert codex[True]["push"] == {"branches": ["main"]}


def test_guard_workflows_publish_unique_required_check_contexts() -> None:
    codex = _load_workflow_path(CODEX_GUARD_WORKFLOW)
    meta = _load_workflow_path(META_GUARD_WORKFLOW)

    assert codex["jobs"]["guard"]["name"] == "codex-guard"
    assert meta["jobs"]["guard"]["name"] == "meta-workflow-guard"


def test_meta_guard_runs_on_dependency_only_pull_requests() -> None:
    """The delivery policy requires Meta Workflow Guard, so its path filter must
    include the dependency files; otherwise a lockfile-only PR never gets the
    check and the policy-authorized merge is skipped (ga-kdbh)."""
    meta = _load_workflow_path(META_GUARD_WORKFLOW)
    paths = meta[True]["pull_request"]["paths"]

    assert "uv.lock" in paths
    assert "pyproject.toml" in paths


def test_dependabot_and_dependency_review_cover_actions_and_uv() -> None:
    dependabot = yaml.safe_load(DEPENDABOT_CONFIG.read_text(encoding="utf-8"))
    updates = dependabot["updates"]

    assert dependabot["version"] == 2
    assert {(entry["package-ecosystem"], entry["directory"]) for entry in updates} == {
        ("github-actions", "/"),
        ("uv", "/"),
    }
    assert all(entry["schedule"]["interval"] == "weekly" for entry in updates)

    workflow = _load_workflow_path(DEPENDENCY_REVIEW_WORKFLOW)
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["dependency-review"]["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["dependency-review"]["timeout-minutes"] == 10


def test_guard_workflows_fail_when_automatic_reference_fixes_are_pending() -> None:
    codex_guard = CODEX_GUARD_WORKFLOW.read_text(encoding="utf-8")
    meta_guard = META_GUARD_WORKFLOW.read_text(encoding="utf-8")

    for workflow_text in (codex_guard, meta_guard):
        assert "Verify no automatic reference fixes are pending" in workflow_text
        assert "python scripts/template-ssot-scanner/apply_reference_fixes.py" in workflow_text
        assert "uv run --frozen --no-sync" in workflow_text
        assert "--dry-run" in workflow_text
        assert "--fail-on-changes" in workflow_text
        assert "--log-file reports/reference-fix-gate/latest.json" in workflow_text
        assert "reports/reference-fix-gate/" in workflow_text
