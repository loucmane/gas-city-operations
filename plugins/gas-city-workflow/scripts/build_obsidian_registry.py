#!/usr/bin/env python3
"""Build the strict Obsidian registry from canonical Gas City project context."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from project_context import (  # noqa: E402
    ContextError,
    _canonical_git_root,
    _load_registry,
    _resolve_git_root,
    build_context,
)
from obsidian_sources import SOURCE_NAME, load_sources  # noqa: E402

PLUGIN_ROOT = SCRIPT_DIR.parent
DEFAULT_WORKFLOW_REGISTRY = PLUGIN_ROOT / "config" / "projects.json"
DEFAULT_OUTPUT = PLUGIN_ROOT / "config" / "obsidian-projects.json"
DEFAULT_HOME = Path("/home/loucmane")
DEFAULT_CITY = DEFAULT_HOME / "gascity" / "city"
DEFAULT_GC = DEFAULT_HOME / "gascity" / "bin" / "gc"
DEFAULT_VAULT_ROOT = DEFAULT_HOME / "vaults" / "main" / "GasCity"
DEFAULT_OBSIDIAN = DEFAULT_HOME / ".local" / "bin" / "obsidian"
DEFAULT_SIGNING_POLICIES = Path("/etc/gas-city-signing/signing-policies.json")


class BuildError(RuntimeError):
    """Raised when project context cannot produce one exact registry."""


def build_payload(
    workflow_registry: Path,
    *,
    canonical_source_root: Path,
    city: Path,
    gc: Path,
    vault_root: Path,
    obsidian_cli: Path,
    signing_policies: Path,
    validate_roots: bool = False,
    obsidian_sources: Path | None = None,
) -> dict[str, Any]:
    try:
        projects = _load_registry(workflow_registry)
        extra, physical_roots = (
            load_sources(obsidian_sources, projects) if obsidian_sources else ([], {})
        )
    except ContextError as exc:
        raise BuildError(str(exc)) from exc
    rendered: list[dict[str, Any]] = []
    for project in projects + extra:
        root = Path(project["root"]).resolve()
        if validate_roots and project in extra:
            try:
                if _resolve_git_root(root) != root or _canonical_git_root(root) != root:
                    raise ContextError("display root must be the canonical Git checkout")
            except ContextError as exc:
                raise BuildError(
                    f"Obsidian project {project['id']} root is invalid: {exc}"
                ) from exc
        if validate_roots and project not in extra:
            try:
                context = build_context(root, workflow_registry)
            except ContextError as exc:
                raise BuildError(f"project {project['id']} context is invalid: {exc}") from exc
            if context["project"]["id"] != project["id"]:
                raise BuildError(f"project {project['id']} resolved to a different identity")
            if Path(context["workspace"]["canonical_root"]) != root:
                raise BuildError(f"project {project['id']} did not resolve to its canonical root")
        project_id = project["id"]
        raw_rig_root = project.get("rig_root")
        if not isinstance(raw_rig_root, str) or not Path(raw_rig_root).is_absolute():
            raise BuildError(f"project {project_id} must declare an absolute rig_root")
        output = vault_root / project_id / "Aegis"
        rendered_project = {
            "id": project_id,
            "enabled": True,
            "target_dir": root.as_posix(),
            "output_dir": output.as_posix(),
            "bead_export_argv": [
                gc.absolute().as_posix(),
                "--city",
                city.resolve().as_posix(),
                "--rig",
                project["rig"],
                "bd",
                "list",
                "--all",
                "--limit",
                "0",
                "--json",
            ],
            "include_bead_content": False,
            "freshness_sla_seconds": 180,
            "min_interval_seconds": 10,
            "export_timeout_seconds": 30,
            "live_index": {
                "obsidian_cli": obsidian_cli.resolve().as_posix(),
                "vault": "main",
                "probe_path": f"GasCity/{project_id}/Aegis/Home.md",
                "timeout_seconds": 30,
            },
        }
        if project["rig"] in physical_roots:
            rendered_project["bead_gate_paths"] = [
                str(Path(raw_rig_root).resolve() / ".beads.gate.lock"),
                physical_roots[project["rig"]] + ".gate.lock",
            ]
        rendered.append(rendered_project)
    if not rendered:
        raise BuildError("workflow registry contains no projects")
    source_root = canonical_source_root.resolve()
    return {
        "schema_version": "1",
        "managed_output_root": vault_root.resolve().as_posix(),
        "continuity_dashboard": {
            "python": "/usr/bin/python3",
            "entrypoint": (
                source_root / "plugins/gas-city-workflow/scripts/continuity.py"
            ).as_posix(),
            "workflow_registry": (
                source_root / "plugins/gas-city-workflow/config/projects.json"
            ).as_posix(),
            "signing_policies": signing_policies.resolve().as_posix(),
            "output_dir": (vault_root / "Continuity").resolve().as_posix(),
            "freshness_sla_seconds": 180,
            "capture_timeout_seconds": 30,
            "live_index": {
                "obsidian_cli": obsidian_cli.resolve().as_posix(),
                "vault": "main",
                "probe_path": "GasCity/Continuity/Status.md",
                "timeout_seconds": 30,
            },
        },
        "projects": rendered,
    }


def render(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--print", action="store_true", dest="print_output")
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--workflow-registry", type=Path, default=DEFAULT_WORKFLOW_REGISTRY)
    parser.add_argument(
        "--obsidian-sources", type=Path, default=PLUGIN_ROOT / "config" / SOURCE_NAME
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--canonical-source-root", type=Path, default=DEFAULT_HOME / "gas-city-ops")
    parser.add_argument("--city", type=Path, default=DEFAULT_CITY)
    parser.add_argument("--gc", type=Path, default=DEFAULT_GC)
    parser.add_argument("--vault-root", type=Path, default=DEFAULT_VAULT_ROOT)
    parser.add_argument("--obsidian-cli", type=Path, default=DEFAULT_OBSIDIAN)
    parser.add_argument("--signing-policies", type=Path, default=DEFAULT_SIGNING_POLICIES)
    parser.add_argument("--validate-roots", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        content = render(
            build_payload(
                args.workflow_registry.resolve(),
                canonical_source_root=args.canonical_source_root,
                city=args.city,
                gc=args.gc,
                vault_root=args.vault_root,
                obsidian_cli=args.obsidian_cli,
                signing_policies=args.signing_policies,
                validate_roots=args.validate_roots,
                obsidian_sources=args.obsidian_sources,
            )
        )
    except (BuildError, OSError) as exc:
        print(f"gas-city-obsidian-registry: BLOCKED: {exc}", file=sys.stderr)
        return 2
    if args.print_output:
        sys.stdout.buffer.write(content)
        return 0
    output = args.output.resolve()
    if args.check:
        if not output.is_file() or output.is_symlink() or output.read_bytes() != content:
            print(f"gas-city-obsidian-registry: BLOCKED: generated registry drift: {output}")
            return 1
        print(f"gas-city-obsidian-registry: PASS {output}")
        return 0
    _atomic_write(output, content)
    print(f"gas-city-obsidian-registry: WROTE {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
