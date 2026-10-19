#!/usr/bin/env python3
"""Render deterministic JSON and human continuity views from one frozen snapshot."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from continuity_model import ContinuityError, build_report, render_status  # noqa: E402
from continuity_capture import (  # noqa: E402
    OBSIDIAN_REGISTRY,
    OBSIDIAN_STATE,
    RESIDUE_DISPOSITIONS,
    SIGNING_POLICIES,
    capture_snapshot,
)
from project_context import DEFAULT_REGISTRY  # noqa: E402


def _load_snapshot(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ContinuityError(f"snapshot must be a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContinuityError(f"snapshot is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContinuityError("snapshot must contain an object")
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("audit", "status"):
        command = subparsers.add_parser(name)
        command.add_argument("--snapshot", required=True, type=Path)
        command.add_argument("--output", type=Path)
    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    snapshot.add_argument("--obsidian-registry", type=Path, default=OBSIDIAN_REGISTRY)
    snapshot.add_argument("--obsidian-state", type=Path, default=OBSIDIAN_STATE)
    snapshot.add_argument(
        "--offline-beads", action="store_true",
        help="Use this cycle's digest-checked reconciler snapshots; never execute gc or bd",
    )
    snapshot.add_argument(
        "--obsidian-cycle-status",
        choices=("idle",),
        help=(
            "Project the post-release registry-cycle status for a reconciler-owned "
            "dashboard candidate"
        ),
    )
    snapshot.add_argument("--signing-policies", type=Path, default=SIGNING_POLICIES)
    snapshot.add_argument(
        "--residue-dispositions", type=Path, default=RESIDUE_DISPOSITIONS
    )
    snapshot.add_argument(
        "--project-root",
        type=Path,
        action="append",
        default=[],
        help="Additional descriptor-onboarded canonical root (repeatable)",
    )
    snapshot.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "snapshot":
            snapshot = capture_snapshot(
                args.registry,
                extra_roots=args.project_root,
                obsidian_registry=args.obsidian_registry,
                obsidian_state=args.obsidian_state,
                offline_beads=args.offline_beads,
                obsidian_cycle_status=args.obsidian_cycle_status,
                signing_policies=args.signing_policies,
                residue_dispositions=args.residue_dispositions,
            )
            rendered = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
            if args.output is None:
                print(rendered, end="")
            else:
                _atomic_write(args.output, rendered)
            return 0
        report = build_report(_load_snapshot(args.snapshot))
    except ContinuityError as exc:
        print(f"gas-city-continuity: BLOCKED: {exc}", file=sys.stderr)
        return 2
    rendered = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.command == "audit"
        else render_status(report)
    )
    if args.output is None:
        print(rendered, end="")
    else:
        _atomic_write(args.output, rendered)
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
