"""Canonical-root retirement and user-level cold-start enforcement tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN = REPO_ROOT / "plugins" / "gas-city-workflow"
POLICY_SCRIPT = PLUGIN / "scripts" / "root_policy.py"
INSTALLER_SCRIPT = PLUGIN / "scripts" / "install_root_policy.py"
PROJECT_CONTEXT_SCRIPT = PLUGIN / "scripts" / "project_context.py"


def _load(path: Path, name: str):
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repository(root: Path, name: str) -> Path:
    root.mkdir(parents=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "remote", "add", "origin", f"git@github.com:fixture/{name}.git")
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "-c", "commit.gpgsign=false", "commit", "-m", "fixture")
    return root


def _policy(path: Path, retired: Path, canonical: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "gas-city-workflow.root-policy.v1",
                "canonical": {
                    "root": canonical.as_posix(),
                    "repository": "fixture/gas-city-operations",
                },
                "retired": [
                    {
                        "root": retired.as_posix(),
                        "repository": "fixture/gas-city-operations",
                        "reason": "preserved historical evidence; new work uses canonical root",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_policy_blocks_retired_checkout_and_its_linked_worktrees(tmp_path: Path) -> None:
    module = _load(POLICY_SCRIPT, "gas_city_root_policy_test")
    retired = _repository(tmp_path / "retired", "gas-city-operations")
    canonical = _repository(tmp_path / "canonical", "gas-city-operations")
    linked = tmp_path / "retired-worktrees" / "ga-old"
    linked.parent.mkdir()
    _git(retired, "worktree", "add", "-b", "codex/ga-old", str(linked))
    policy = _policy(tmp_path / "root-policy.json", retired, canonical)

    for candidate in (retired, linked, linked / "nested"):
        if candidate.name == "nested":
            candidate.mkdir()
        decision = module.evaluate_root(candidate, policy)
        assert decision["classification"] == "retired"
        assert decision["canonical_root"] == canonical.as_posix()
        with pytest.raises(module.RootPolicyError, match=canonical.as_posix()):
            module.require_active_root(candidate, policy)

    assert module.evaluate_root(canonical, policy)["classification"] == "canonical"
    assert module.evaluate_root(tmp_path, policy)["classification"] == "unmanaged"


def test_hook_denies_mutation_from_retired_root_and_allows_canonical_root(
    tmp_path: Path,
) -> None:
    module = _load(POLICY_SCRIPT, "gas_city_root_policy_hook_test")
    retired = _repository(tmp_path / "retired", "gas-city-operations")
    canonical = _repository(tmp_path / "canonical", "gas-city-operations")
    policy = _policy(tmp_path / "root-policy.json", retired, canonical)
    payload = {"tool_name": "Bash", "tool_input": {"command": "touch source.txt"}}

    denied = module.evaluate_hook(payload, policy, process_cwd=retired)
    allowed = module.evaluate_hook(payload, policy, process_cwd=canonical)

    assert denied["decision"] == "deny"
    assert "historical" in denied["reason"]
    assert canonical.as_posix() in denied["reason"]
    assert allowed == {"decision": "allow", "reason": "root is not retired"}


def test_project_context_uses_shared_retirement_policy_before_registry_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_policy = _load(POLICY_SCRIPT, "root_policy")
    context = _load(PROJECT_CONTEXT_SCRIPT, "gas_city_project_context_policy_test")
    retired = _repository(tmp_path / "retired", "gas-city-operations")
    canonical = _repository(tmp_path / "canonical", "gas-city-operations")
    policy = _policy(tmp_path / "root-policy.json", retired, canonical)
    registry = tmp_path / "projects.json"
    registry.write_text(
        '{"schema":"gas-city-workflow.project-registry.v1","projects":[]}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(context, "DEFAULT_ROOT_POLICY", policy)

    with pytest.raises(context.ContextError, match=canonical.as_posix()):
        context.build_context(retired, registry)

    assert root_policy.evaluate_root(canonical, policy)["classification"] == "canonical"


def test_canonical_context_passes_in_both_idle_and_active_task_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load(POLICY_SCRIPT, "root_policy")
    context = _load(PROJECT_CONTEXT_SCRIPT, "gas_city_project_context_lifecycle_test")
    retired = _repository(tmp_path / "retired", "gas-city-operations")
    canonical = _repository(tmp_path / "canonical", "gas-city-operations")
    policy = _policy(tmp_path / "root-policy.json", retired, canonical)
    registry = tmp_path / "projects.json"
    registry.write_text(
        json.dumps(
            {
                "schema": "gas-city-workflow.project-registry.v1",
                "projects": [
                    {
                        "id": "gas-city-operations",
                        "root": canonical.as_posix(),
                        "repository": "fixture/gas-city-operations",
                        "rig": "gascity",
                        "workflow_authority": "beads",
                        "workflow_profile": "beads-with-aegis-evidence",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(context, "DEFAULT_ROOT_POLICY", policy)

    idle = context.build_context(canonical, registry)
    active = canonical / "docs/ai/work-tracking/active/20300101-ga-active-ACTIVE"
    active.mkdir(parents=True)
    running = context.build_context(canonical, registry)

    assert idle["workflow"]["active_trackers"] == []
    assert running["workflow"]["active_trackers"] == [active.name]
    assert idle["project"] == running["project"]
    assert idle["workspace"] == running["workspace"]


def test_installer_renders_both_user_hooks_and_preserves_unrelated_settings() -> None:
    module = _load(INSTALLER_SCRIPT, "gas_city_root_policy_installer_render_test")
    command = (
        "/usr/bin/python3 /home/example/.local/libexec/gas-city-workflow/"
        "root-policy-v1/root-policy "
        "--hook --policy /home/example/.local/libexec/gas-city-workflow/"
        "root-policy-v1/root-policy.json"
    )
    codex_before = b'{"version": 1, "hooks": {"SessionStart": []}, "keep": {"x": true}}\n'
    claude_before = b'{"permissions":{"allow":["Read"]},"theme":"dark"}\n'

    codex_after = module.render_hooks_config(codex_before, command, platform="codex")
    claude_after = module.render_hooks_config(claude_before, command, platform="claude")

    for before, after in ((codex_before, codex_after), (claude_before, claude_after)):
        old = json.loads(before)
        new = json.loads(after)
        assert new["hooks"]["PreToolUse"][-1] == module.hook_registration(command)
        assert {key: value for key, value in new.items() if key != "hooks"} == {
            key: value for key, value in old.items() if key != "hooks"
        }
        assert module.render_hooks_config(after, command, platform="codex") == after


def test_installer_changes_only_retired_codex_trust_and_claude_aegis_source() -> None:
    module = _load(INSTALLER_SCRIPT, "gas_city_root_policy_installer_config_test")
    codex_before = b"""model = "gpt-5.6-sol"\n\n[projects."/home/loucmane/codex"]\ntrust_level = "trusted"\nkeep = "old"\n\n[projects."/home/loucmane/gas-city-ops"]\ntrust_level = "trusted"\n\n[unrelated]\nvalue = 7\n"""
    claude_before = (
        json.dumps(
            {
                "mcpServers": {
                    "aegis": {
                        "command": "uvx",
                        "args": ["--from", "/home/loucmane/codex", "aegis-mcp-server"],
                    },
                    "keep": {"command": "true"},
                },
                "keep": [1, 2, 3],
            },
            indent=2,
        ).encode()
        + b"\n"
    )

    codex_after = module.render_codex_config(codex_before)
    claude_after = module.render_claude_config(claude_before)

    parsed = tomllib.loads(codex_after.decode())
    assert parsed["projects"]["/home/loucmane/codex"]["trust_level"] == "untrusted"
    assert parsed["projects"]["/home/loucmane/gas-city-ops"]["trust_level"] == "trusted"
    assert parsed["projects"]["/home/loucmane/codex"]["keep"] == "old"
    assert parsed["unrelated"] == {"value": 7}
    assert module.render_codex_config(codex_after) == codex_after
    claude = json.loads(claude_after)
    assert claude["mcpServers"]["aegis"]["args"][1] == "/home/loucmane/gas-city-ops"
    assert claude["mcpServers"]["keep"] == {"command": "true"}
    assert claude["keep"] == [1, 2, 3]
    assert module.render_claude_config(claude_after) == claude_after


def test_transaction_rolls_back_every_target_on_postwrite_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load(INSTALLER_SCRIPT, "gas_city_root_policy_installer_rollback_test")
    retired = _repository(tmp_path / "retired", "gas-city-operations")
    canonical = _repository(tmp_path / "canonical", "gas-city-operations")
    monkeypatch.setattr(module, "RETIRED_ROOT", retired.as_posix())
    monkeypatch.setattr(module, "CANONICAL_ROOT", canonical.as_posix())
    policy = _policy(tmp_path / "root-policy.json", retired, canonical)
    runtime = tmp_path / "runtime"
    codex_home = tmp_path / ".codex"
    claude_home = tmp_path / ".claude"
    codex_home.mkdir()
    claude_home.mkdir()
    codex_hooks = codex_home / "hooks.json"
    claude_settings = claude_home / "settings.json"
    codex_config = codex_home / "config.toml"
    claude_config = tmp_path / ".claude.json"
    codex_config.write_text(
        f'[projects."{retired}"]\ntrust_level = "trusted"\n'
        f'[projects."{canonical}"]\ntrust_level = "trusted"\n',
        encoding="utf-8",
    )
    claude_settings.write_text('{"theme":"dark"}\n', encoding="utf-8")
    claude_config.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "aegis": {
                        "args": ["--from", retired.as_posix(), "aegis-mcp-server"]
                    }
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    before = {path: path.read_bytes() for path in (codex_config, claude_settings, claude_config)}

    def refuse_trust(*_args, **_kwargs):
        raise module.InstallError("synthetic postwrite trust failure")

    with pytest.raises(module.InstallError, match="synthetic postwrite"):
        module.install(
            policy_source=policy,
            runtime_source=POLICY_SCRIPT,
            runtime_dir=runtime,
            codex_hooks=codex_hooks,
            claude_settings=claude_settings,
            codex_config=codex_config,
            claude_config=claude_config,
            evidence_root=tmp_path / "evidence",
            hook_truster=refuse_trust,
        )

    assert {path: path.read_bytes() for path in before} == before
    assert not codex_hooks.exists()
    assert not runtime.exists()
    failure = json.loads((tmp_path / "evidence" / "result.json").read_text(encoding="utf-8"))
    assert failure["status"] == "fail"
    assert failure["rollback"] == "pass"


def test_transaction_is_successful_and_idempotent_with_exact_fixture_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load(INSTALLER_SCRIPT, "gas_city_root_policy_installer_success_test")
    retired = _repository(tmp_path / "retired", "gas-city-operations")
    canonical = _repository(tmp_path / "canonical", "gas-city-operations")
    monkeypatch.setattr(module, "RETIRED_ROOT", retired.as_posix())
    monkeypatch.setattr(module, "CANONICAL_ROOT", canonical.as_posix())
    policy = _policy(tmp_path / "root-policy.json", retired, canonical)
    runtime = tmp_path / "home/.local/libexec/gas-city-workflow/root-policy-v1"
    codex_home = tmp_path / "home/.codex"
    claude_home = tmp_path / "home/.claude"
    codex_home.mkdir(parents=True)
    claude_home.mkdir(parents=True)
    codex_hooks = codex_home / "hooks.json"
    claude_settings = claude_home / "settings.json"
    codex_config = codex_home / "config.toml"
    claude_config = tmp_path / "home/.claude.json"
    codex_config.write_text(
        f'[projects."{retired}"]\ntrust_level = "trusted"\n'
        f'[projects."{canonical}"]\ntrust_level = "trusted"\n',
        encoding="utf-8",
    )
    claude_settings.write_text('{"theme":"dark"}\n', encoding="utf-8")
    claude_config.write_text(
        json.dumps(
            {"mcpServers": {"aegis": {"args": ["--from", retired.as_posix(), "aegis-mcp-server"]}}}
        )
        + "\n",
        encoding="utf-8",
    )

    def trust(*_args, **_kwargs):
        return {"status": "trusted-fixture"}

    first = module.install(
        policy_source=policy,
        runtime_source=POLICY_SCRIPT,
        runtime_dir=runtime,
        codex_hooks=codex_hooks,
        claude_settings=claude_settings,
        codex_config=codex_config,
        claude_config=claude_config,
        evidence_root=tmp_path / "evidence-1",
        hook_truster=trust,
    )
    after_first = {
        path: path.read_bytes()
        for path in (
            runtime / "root-policy",
            runtime / "root-policy.json",
            codex_hooks,
            claude_settings,
            codex_config,
            claude_config,
        )
    }
    second = module.install(
        policy_source=policy,
        runtime_source=POLICY_SCRIPT,
        runtime_dir=runtime,
        codex_hooks=codex_hooks,
        claude_settings=claude_settings,
        codex_config=codex_config,
        claude_config=claude_config,
        evidence_root=tmp_path / "evidence-2",
        hook_truster=trust,
    )

    assert first["status"] == second["status"] == "pass"
    assert {path: path.read_bytes() for path in after_first} == after_first
    assert json.loads(codex_hooks.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    assert json.loads(claude_settings.read_text(encoding="utf-8"))["theme"] == "dark"
    assert (
        tomllib.loads(codex_config.read_text(encoding="utf-8"))["projects"][retired.as_posix()][
            "trust_level"
        ]
        == "untrusted"
    )


def test_repository_policy_matches_migration_identity() -> None:
    policy = json.loads((PLUGIN / "config" / "root-policy.json").read_text(encoding="utf-8"))
    migration = json.loads(
        (REPO_ROOT / "config" / "gas-city-operations-migration.json").read_text(encoding="utf-8")
    )

    assert policy["canonical"] == {
        "root": migration["workspace"]["canonical_root"],
        "repository": migration["repository"]["canonical_full_name"],
    }
    assert policy["retired"] == [
        {
            "root": migration["workspace"]["legacy_root"],
            "repository": migration["repository"]["canonical_full_name"],
            "reason": "preserved historical evidence; new work uses canonical root",
        }
    ]
    assert migration["workspace"]["legacy_retirement"] == "user-hooks-and-shared-root-policy"
