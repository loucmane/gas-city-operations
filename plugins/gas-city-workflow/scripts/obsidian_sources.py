"""Projection-only sources; never an input to workflow policy or delegation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from project_context import ContextError, ID_PATTERN, _validate_project

SOURCE_NAME = "obsidian-sources.json"


def load_sources(
    path: Path, workflow_projects: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if path.is_symlink() or not path.is_file():
        raise ContextError(f"Obsidian sources must be a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ContextError(f"invalid Obsidian sources: {path}") from exc
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema", "projects", "physical_roots"}
        or payload["schema"] != "gas-city-obsidian.sources.v1"
        or not isinstance(payload["projects"], list)
        or not all(isinstance(p, dict) for p in payload["projects"])
        or not isinstance(payload["physical_roots"], dict)
    ):
        raise ContextError("invalid Obsidian sources schema")
    projects = [_validate_project(p, allow_root=True) for p in payload["projects"]]
    combined = workflow_projects + projects
    for field in ("id", "root"):
        values = [p[field] if field == "id" else str(Path(p[field]).resolve()) for p in combined]
        if len(set(values)) != len(values):
            raise ContextError(f"Obsidian sources collide with a project {field}")
    physical_roots = payload["physical_roots"]
    for rig, root in physical_roots.items():
        if (
            not ID_PATTERN.fullmatch(rig)
            or not isinstance(root, str)
            or not Path(root).is_absolute()
            or Path(root).as_posix() != root
            or ".." in Path(root).parts
            or any(ord(c) < 32 or ord(c) == 127 for c in root)
        ):
            raise ContextError("Obsidian physical roots must bind rigs to exact absolute paths")
    return projects, physical_roots
