"""Standalone CLI for the installed Aegis Obsidian reconciler."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from aegis_foundation.obsidian_reconciler import (
    CHECK_LOCK_TIMEOUT_SECONDS,
    check_registry,
    reconcile_registry,
)
from aegis_foundation.obsidian_registry import RegistryError, load_registry
from aegis_foundation.obsidian_exports import export_registry


def _default_state() -> Path:
    return Path.home() / ".local" / "state" / "aegis" / "obsidian-reconciler"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aegis-obsidian-reconcile")
    subparsers = parser.add_subparsers(dest="command", required=True)
    export = subparsers.add_parser("export")
    export.add_argument("--registry", required=True)
    for name in ("run", "check"):
        command = subparsers.add_parser(name)
        command.add_argument("--registry", required=True)
        command.add_argument("--state-dir", default=str(_default_state()))
    subparsers.choices["run"].add_argument("--force", action="store_true")
    subparsers.choices["check"].add_argument(
        "--require-live-index",
        action="store_true",
        help="require a current managed-note read through host Obsidian IPC",
    )
    subparsers.choices["check"].add_argument(
        "--lock-timeout-seconds",
        type=float,
        default=CHECK_LOCK_TIMEOUT_SECONDS,
        help=(
            "bounded wait for an active reconciliation before checking "
            f"(default: {CHECK_LOCK_TIMEOUT_SECONDS:g})"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        registry = load_registry(args.registry)
        if args.command == "export":
            result = export_registry(registry)
        elif args.command == "run":
            result = reconcile_registry(
                registry,
                state_dir=args.state_dir,
                force=args.force,
            )
        else:
            result = check_registry(
                registry,
                state_dir=args.state_dir,
                require_live_index=args.require_live_index,
                lock_timeout_seconds=args.lock_timeout_seconds,
            )
    except (RegistryError, OSError, RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": "1",
                    "ok": False,
                    "status": "refused",
                    "error": " ".join(str(exc).split())[:1_000],
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
