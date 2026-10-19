from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest

from aegis_foundation.obsidian_registry import load_registry

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN = REPO_ROOT / "plugins" / "gas-city-workflow"
SCRIPT = PLUGIN / "scripts" / "build_obsidian_registry.py"
WORKFLOW_REGISTRY = PLUGIN / "config" / "projects.json"
OBSIDIAN_REGISTRY = PLUGIN / "config" / "obsidian-projects.json"
OBSIDIAN_SOURCES = PLUGIN / "config" / "obsidian-sources.json"


def _module():
    name = "gas_city_obsidian_registry_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_tracked_registry_is_exact_generated_projection_of_project_registry() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    workflow = json.loads(WORKFLOW_REGISTRY.read_text(encoding="utf-8"))
    sources = json.loads(OBSIDIAN_SOURCES.read_text(encoding="utf-8"))
    projects = workflow["projects"] + sources["projects"]
    obsidian = load_registry(OBSIDIAN_REGISTRY)
    assert obsidian.export_dir == Path("/home/loucmane/.local/state/aegis/obsidian-exports")
    assert obsidian.export_max_age_seconds == 600
    assert obsidian.managed_output_root == Path("/home/loucmane/vaults/main/GasCity")
    assert [project.id for project in obsidian.projects] == [project["id"] for project in projects]
    for source, project in zip(projects, obsidian.projects, strict=True):
        assert project.target_dir == Path(source["root"])
        assert project.output_dir == Path(
            f"/home/loucmane/vaults/main/GasCity/{source['id']}/Aegis"
        )
        assert project.bead_export_argv == (
            "/home/loucmane/gascity/bin/gc",
            "--city",
            "/home/loucmane/gascity/city",
            "--rig",
            source["rig"],
            "bd",
            "list",
            "--all",
            "--limit",
            "0",
            "--json",
        )
        assert project.live_index is not None
        assert project.bead_gate_paths == (
            Path(source["rig_root"] + "/.beads.gate.lock"),
            Path(sources["physical_roots"][source["rig"]] + ".gate.lock"),
        )
        assert project.live_index.probe_path == f"GasCity/{source['id']}/Aegis/Home.md"
    assert obsidian.continuity_dashboard is not None
    assert obsidian.continuity_dashboard.output_dir == Path(
        "/home/loucmane/vaults/main/GasCity/Continuity"
    )
    assert obsidian.continuity_dashboard.workflow_registry == Path(
        "/home/loucmane/gas-city-ops/plugins/gas-city-workflow/config/projects.json"
    )


def test_canonical_policy_registry_remains_byte_identical_to_head() -> None:
    baseline = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "show",
            "HEAD:plugins/gas-city-workflow/config/projects.json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    ).stdout
    assert WORKFLOW_REGISTRY.read_bytes() == baseline


@pytest.mark.parametrize("field", ["id", "root"])
def test_obsidian_sources_cannot_override_workflow_identity(tmp_path, field):
    module = _module()
    workflow = json.loads(WORKFLOW_REGISTRY.read_text())["projects"]
    source = json.loads(OBSIDIAN_SOURCES.read_text())
    source["projects"][0][field] = workflow[0][field]
    path = tmp_path / "obsidian-sources.json"
    path.write_text(json.dumps(source))
    with pytest.raises(module.ContextError, match="collide"):
        module.load_sources(path, workflow)


def test_obsidian_sources_are_not_a_workflow_policy_registry():
    module = _module()
    with pytest.raises(module.ContextError, match="schema"):
        module._load_registry(OBSIDIAN_SOURCES)


def test_descriptor_onboarding_changes_one_generated_project_entry(tmp_path: Path) -> None:
    module = _module()
    source = json.loads(WORKFLOW_REGISTRY.read_text(encoding="utf-8"))
    source["projects"].append(
        {
            "id": "future-project",
            "root": "/srv/future-project",
            "rig_root": "/srv/gascity/rigs/future-project",
            "repository": "example/future-project",
            "rig": "future-project",
            "workflow_authority": "beads",
            "workflow_profile": "beads-with-aegis-evidence",
        }
    )
    registry = tmp_path / "projects.json"
    registry.write_text(json.dumps(source), encoding="utf-8")

    payload = module.build_payload(
        registry,
        canonical_source_root=Path("/srv/gas-city-ops"),
        city=Path("/srv/gascity/city"),
        gc=Path("/srv/gascity/bin/gc"),
        vault_root=Path("/srv/vault/GasCity"),
        obsidian_cli=Path("/srv/bin/obsidian"),
        signing_policies=Path("/etc/signing.json"),
    )

    project = payload["projects"][-1]
    assert project["id"] == "future-project"
    assert project["target_dir"] == "/srv/future-project"
    assert project["output_dir"] == "/srv/vault/GasCity/future-project/Aegis"
    assert project["bead_export_argv"] == [
        "/srv/gascity/bin/gc",
        "--city",
        "/srv/gascity/city",
        "--rig",
        "future-project",
        "bd",
        "list",
        "--all",
        "--limit",
        "0",
        "--json",
    ]
    assert project["live_index"]["probe_path"] == "GasCity/future-project/Aegis/Home.md"


def test_registry_covers_all_eight_projects_with_explicit_rig_stores() -> None:
    registry = load_registry(OBSIDIAN_REGISTRY)
    expected = {
        "gas-city-operations": "gascity",
        "gas-city": "gascity",
        "hpfetcher": "hpfetcher",
        "blog": "blog",
        "gas-city-template": "gas-city-template",
        "bounty": "bounty",
        "vernissage": "vernissage",
        "harpoon": "harpoon",
    }
    assert {project.id: project.bead_export_argv[4] for project in registry.projects} == expected
    for project in registry.projects:
        if project.id in {"bounty", "vernissage", "harpoon"}:
            assert project.target_dir == Path(f"/home/loucmane/dev/{project.id}")
