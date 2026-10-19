from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from aegis_foundation import cli as aegis_cli
from aegis_foundation import obsidian_vault

SOURCE_ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return result.stdout.strip()


def _repo(tmp_path: Path, *, task_count: int = 2) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    _run("git", "init", "-q", "-b", "main", cwd=root)
    _run("git", "config", "user.name", "Aegis Test", cwd=root)
    _run("git", "config", "user.email", "aegis@example.invalid", cwd=root)
    tasks = []
    for task_id in range(1, task_count + 1):
        tasks.append(
            {
                "id": task_id,
                "title": f"Task {task_id} title",
                "description": f"Bounded description for task {task_id}",
                "status": "in-progress" if task_id == 1 else "pending",
                "priority": "high",
                "dependencies": [] if task_id == 1 else [task_id - 1],
                "subtasks": [],
            }
        )
    task_dir = root / ".taskmaster" / "tasks"
    task_dir.mkdir(parents=True)
    (task_dir / "tasks.json").write_text(
        json.dumps({"master": {"tasks": tasks}}, indent=2) + "\n",
        encoding="utf-8",
    )
    capsule_dir = root / ".aegis" / "capsule"
    capsule_dir.mkdir(parents=True)
    (capsule_dir / "current.json").write_text(
        json.dumps(
            {
                "active_task": {"id": "1", "title": "Task 1 title", "status": "in-progress"},
                "next_action": "continue_task_1",
                "orientation_source": "branch",
                "branch": "feat/task-1-vault",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    tracker = root / "docs" / "ai" / "work-tracking" / "active" / "task1" / "TRACKER.md"
    tracker.parent.mkdir(parents=True)
    tracker.write_text(
        "# Task 1 Tracker\n\n"
        "- [ ] Human decision that must remain preserved\n"
        "- [S:one|W:task-1|H:human|E:note] Human evidence\n\n"
        "<!-- AEGIS:BEGIN generated-sweh-projection -->\n"
        "- [S:auto|W:task-1|H:generated|E:ledger:event] Generated evidence\n"
        "<!-- AEGIS:END generated-sweh-projection -->\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# Test repository\n", encoding="utf-8")
    _run("git", "add", ".", cwd=root)
    _run("git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", "fixture", cwd=root)
    _run("git", "switch", "-q", "-c", "feat/task-1-vault", cwd=root)
    return root


def _events(root: Path) -> list[dict[str, object]]:
    head = _run("git", "rev-parse", "HEAD", cwd=root)
    base = {
        "repository_identity": "sha256:fixture",
        "worktree_root": root.as_posix(),
        "branch": "feat/task-1-vault",
        "head": head,
        "session_id": "session-one",
        "agent_id": "agent-child",
        "agent_type": "codex",
        "parent_agent_id": "agent-parent",
    }
    return [
        {
            **base,
            "event_id": "event-session",
            "ts": "2026-07-14T10:00:00Z",
            "event_type": "session_begin",
            "handler": "codex:sessionstart",
            "outcome": "pass",
            "paths": [],
            "extra": {"source": "resume"},
        },
        {
            **base,
            "event_id": "event-scope",
            "ts": "2026-07-14T10:01:00Z",
            "event_type": "scope",
            "handler": "codex:scope",
            "outcome": "pass",
            "paths": [],
            "extra": {"task_id": "1", "work_id": "task-1"},
        },
        {
            **base,
            "event_id": "event-verify",
            "ts": "2026-07-14T10:02:00Z",
            "event_type": "verification",
            "handler": "codex:verify",
            "outcome": "pass",
            "exit_class": "pass",
            "paths": ["reports/verification.json"],
            "extra": {"task_id": "1", "gate": "tests", "package": "app"},
        },
        {
            **base,
            "event_id": "event-witness",
            "ts": "2026-07-14T10:03:00Z",
            "event_type": "witness",
            "handler": "codex:witness",
            "outcome": "pass",
            "paths": [".aegis/reports/witness-report.json"],
            "extra": {
                "task_id": "1",
                "passed": True,
                "report_path": ".aegis/reports/witness-report.json",
            },
        },
        {
            **base,
            "event_id": "event-delivery",
            "ts": "2026-07-14T10:04:00Z",
            "event_type": "delivery",
            "handler": "github:delivery",
            "outcome": "pass",
            "paths": [],
            "extra": {"task_id": "1", "pr_number": 42, "action": "merged"},
        },
        {
            **base,
            "agent_id": "agent-low-level-only",
            "event_id": "event-mutation",
            "ts": "2026-07-14T10:05:00Z",
            "event_type": "mutation",
            "tool_name": "Bash",
            "handler": "codex:bash",
            "outcome": "pass",
            "paths": ["src/example.py"],
            "extra": {"command": "curl -H 'Authorization: Bearer github_pat_secretvalue'"},
        },
        {
            **base,
            "event_id": "event-gate",
            "ts": "2026-07-14T10:06:00Z",
            "event_type": "gate_decision",
            "handler": "codex:pretooluse",
            "outcome": "pass",
            "paths": ["src/example.py"],
            "extra": {"reason": "allowed"},
        },
    ]


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _bead_snapshot(path: Path) -> Path:
    path.write_text(
        json.dumps(
            [
                {
                    "id": "ga-zbmk",
                    "title": "Sensitive title off by default",
                    "description": "Sensitive description off by default",
                    "status": "in_progress",
                    "priority": 2,
                    "issue_type": "feature",
                    "owner": "lookmanbenali@gmail.com",
                    "labels": ["aegis", "obsidian"],
                    "metadata": {"gc.branch": "codex/ga-zbmk-aegis-beads-obsidian"},
                    "dependencies": [],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_builds_deterministic_bounded_graph_and_preserves_legacy_context(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    events = _events(root)
    snapshot = obsidian_vault.collect_snapshot(root, events)
    output = tmp_path / "vault"

    first = obsidian_vault.build_vault(snapshot, output, target_dir=root)
    assert first["status"] == "built"
    assert first["changed"] is True
    before = _tree_digest(output)

    assert (output / "Home.md").is_file()
    assert (output / "Tasks" / "task-1.md").is_file()
    assert (output / "Views" / "Tasks.base").is_file()
    assert list((output / "Evidence" / "witness").glob("*.md"))
    assert list((output / "Evidence" / "verification").glob("*.md"))
    assert list((output / "Evidence" / "delivery").glob("*.md"))
    assert len(list((output / "Legacy").glob("*.md"))) == 1
    assert len(list((output / "Agents").glob("*.md"))) == 3

    all_text = "\n".join(
        path.read_text(encoding="utf-8") for path in output.rglob("*") if path.is_file()
    )
    assert "[[Tasks/task-1|Task 1]]" in all_text
    assert "Parent agent: agent-parent" in all_text
    assert "agent-low-level-only" in all_text
    assert "Human-authored nonblank lines: 3" in all_text
    assert "Generated Aegis blocks: 1" in all_text
    assert "event-mutation" not in all_text
    assert "event-gate" not in all_text
    assert "github_pat_secretvalue" not in all_text
    assert "curl -H" not in all_text

    second = obsidian_vault.build_vault(snapshot, output, target_dir=root)
    assert second["status"] == "current"
    assert second["changed"] is False
    assert _tree_digest(output) == before
    assert obsidian_vault.check_vault(output, expected_source_digest=snapshot["source_digest"])[
        "ok"
    ]

    # New low-level hook traffic must not churn the knowledge graph or freshness digest.
    more_low_level = [
        *events,
        {
            **events[-1],
            "event_id": "another-gate",
            "ts": "2026-07-14T10:07:00Z",
        },
    ]
    quiet_snapshot = obsidian_vault.collect_snapshot(root, more_low_level)
    assert quiet_snapshot["source_digest"] == snapshot["source_digest"]

    new_identity = [
        *events,
        {
            **events[-1],
            "agent_id": "new-agent",
            "event_id": "new-agent-gate",
            "ts": "2026-07-14T10:07:30Z",
        },
    ]
    identity_snapshot = obsidian_vault.collect_snapshot(root, new_identity)
    assert identity_snapshot["source_digest"] != snapshot["source_digest"]

    high_signal_change = [
        *events,
        {
            **events[2],
            "event_id": "new-verification",
            "ts": "2026-07-14T10:08:00Z",
        },
    ]
    changed_snapshot = obsidian_vault.collect_snapshot(root, high_signal_change)
    assert changed_snapshot["source_digest"] != snapshot["source_digest"]


def test_refuses_in_repo_unknown_or_tampered_destinations(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    snapshot = obsidian_vault.collect_snapshot(root, _events(root))

    with pytest.raises(obsidian_vault.VaultError, match="outside the source repository"):
        obsidian_vault.build_vault(snapshot, root / "vault", target_dir=root)

    unknown = tmp_path / "unknown"
    unknown.mkdir()
    (unknown / "my-note.md").write_text("manual\n", encoding="utf-8")
    with pytest.raises(obsidian_vault.VaultError, match="untrusted or modified vault"):
        obsidian_vault.build_vault(snapshot, unknown, target_dir=root)
    assert (unknown / "my-note.md").read_text(encoding="utf-8") == "manual\n"

    managed = tmp_path / "managed"
    obsidian_vault.build_vault(snapshot, managed, target_dir=root)
    (managed / "Home.md").write_text("tampered\n", encoding="utf-8")
    check = obsidian_vault.check_vault(managed)
    assert check["ok"] is False
    assert "hash mismatch: Home.md" in check["problems"]
    with pytest.raises(obsidian_vault.VaultError, match="hash mismatch"):
        obsidian_vault.build_vault(snapshot, managed, target_dir=root)

    symlink = tmp_path / "vault-symlink"
    symlink.symlink_to(unknown, target_is_directory=True)
    with pytest.raises(obsidian_vault.VaultError, match="must not be a symlink"):
        obsidian_vault.build_vault(snapshot, symlink, target_dir=root)
    assert obsidian_vault.check_vault(symlink)["ok"] is False


def test_rebuild_repairs_only_digest_proven_missing_owned_files(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    snapshot = obsidian_vault.collect_snapshot(root, _events(root))
    output = tmp_path / "managed-repair"
    obsidian_vault.build_vault(snapshot, output, target_dir=root)
    missing = output / "Home.md"
    expected = missing.read_bytes()
    missing.unlink()

    check = obsidian_vault.check_vault(output)
    assert check["ok"] is False
    assert "missing owned files: Home.md" in check["problems"]

    repaired = obsidian_vault.build_vault(snapshot, output, target_dir=root)

    assert repaired["status"] == "repaired"
    assert repaired["changed"] is True
    assert missing.read_bytes() == expected
    assert obsidian_vault.check_vault(
        output, expected_source_digest=snapshot["source_digest"]
    )["ok"]


def test_missing_owned_repair_refuses_unknown_or_modified_survivors(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    snapshot = obsidian_vault.collect_snapshot(root, _events(root))
    output = tmp_path / "managed-repair-refusal"
    obsidian_vault.build_vault(snapshot, output, target_dir=root)
    (output / "Home.md").unlink()
    (output / "README.md").write_text("modified\n", encoding="utf-8")

    with pytest.raises(obsidian_vault.VaultError, match="hash mismatch: README.md"):
        obsidian_vault.build_vault(snapshot, output, target_dir=root)


def test_atomic_replace_restores_previous_vault_when_publish_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    events = _events(root)
    first_snapshot = obsidian_vault.collect_snapshot(root, events)
    output = tmp_path / "atomic-vault"
    obsidian_vault.build_vault(first_snapshot, output, target_dir=root)
    original_digest = _tree_digest(output)

    changed_snapshot = obsidian_vault.collect_snapshot(
        root,
        [
            *events,
            {
                **events[2],
                "event_id": "later-verification",
                "ts": "2026-07-14T11:00:00Z",
            },
        ],
    )
    real_replace = obsidian_vault.os.replace
    calls = 0

    def fail_second_replace(source: object, destination: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated publish failure")
        real_replace(source, destination)

    monkeypatch.setattr(obsidian_vault.os, "replace", fail_second_replace)
    with pytest.raises(OSError, match="simulated publish failure"):
        obsidian_vault.build_vault(changed_snapshot, output, target_dir=root)

    assert output.is_dir()
    assert _tree_digest(output) == original_digest
    assert obsidian_vault.check_vault(
        output, expected_source_digest=first_snapshot["source_digest"]
    )["ok"]


def test_limits_fail_closed_before_rendering_unbounded_task_graph(tmp_path: Path) -> None:
    root = _repo(tmp_path, task_count=2)
    with pytest.raises(obsidian_vault.VaultError, match="exceeds task limit"):
        obsidian_vault.collect_snapshot(
            root,
            [],
            limits=obsidian_vault.VaultLimits(max_tasks=1),
        )
    with pytest.raises(obsidian_vault.VaultError, match="agent_id limit"):
        obsidian_vault.collect_snapshot(
            root,
            _events(root),
            limits=obsidian_vault.VaultLimits(max_agents=1),
        )


def test_default_identity_ceiling_covers_large_bounded_project_history(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    events = [
        {
            "event_id": f"event-{index:04d}",
            "ts": f"2026-07-14T10:{index % 60:02d}:00Z",
            "event_type": "session_begin",
            "agent_id": f"agent-{index:04d}",
        }
        for index in range(2_421)
    ]

    snapshot = obsidian_vault.collect_snapshot(root, events)

    assert len(snapshot["identities"]) == 2_421
    assert snapshot["limits"]["max_agents"] == snapshot["limits"]["max_identity_edges"]


def test_linked_worktree_uses_common_repository_name_and_identity(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sibling = tmp_path / "agent-worktree"
    _run("git", "worktree", "add", "-q", "-b", "feat/task-2-agent", str(sibling), cwd=root)

    root_snapshot = obsidian_vault.collect_snapshot(root, [])
    sibling_snapshot = obsidian_vault.collect_snapshot(sibling, [])

    assert root_snapshot["repository"]["name"] == "project"
    assert sibling_snapshot["repository"]["name"] == "project"
    assert root_snapshot["repository"]["identity"] == sibling_snapshot["repository"]["identity"]
    assert sibling_snapshot["repository"]["branch"] == "feat/task-2-agent"


def test_cli_build_and_check_use_explicit_out_of_repo_destination(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path)
    output = tmp_path / "cli-vault"
    args = [
        "--source-root",
        str(SOURCE_ROOT),
        "vault",
        "build",
        "--target-dir",
        str(root),
        "--output",
        str(output),
    ]
    assert aegis_cli.main(args) == 0
    built = json.loads(capsys.readouterr().out)
    assert built["status"] == "built"
    assert built["authority"] == "derived-read-only"
    assert built["ledger"] == "absent"

    check_args = [
        "--source-root",
        str(SOURCE_ROOT),
        "vault",
        "check",
        "--target-dir",
        str(root),
        "--output",
        str(output),
    ]
    assert aegis_cli.main(check_args) == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["ok"] is True
    assert checked["fresh"] is True

    inside_args = [
        "--source-root",
        str(SOURCE_ROOT),
        "vault",
        "build",
        "--target-dir",
        str(root),
        "--output",
        str(root / "forbidden-vault"),
    ]
    assert aegis_cli.main(inside_args) == 1
    assert "outside the source repository" in capsys.readouterr().err


def test_bead_projection_and_closeout_gate_are_authority_aware(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    source = _bead_snapshot(tmp_path / "beads.json")
    events = [
        {
            **_events(root)[2],
            "event_id": "bead-verification",
            "branch": "codex/ga-zbmk-aegis-beads-obsidian",
            "extra": {"gate": "tests", "passed": True},
        }
    ]
    snapshot = obsidian_vault.collect_snapshot(root, events, bead_snapshot=source)
    output = tmp_path / "aegis-subtree"

    built = obsidian_vault.build_vault(snapshot, output, target_dir=root)
    assert built["status"] == "built"
    assert (output / "Beads" / "ga-zbmk.md").is_file()
    assert (output / "Views" / "Work.base").is_file()
    assert not (output / "Tasks" / "task-1.md").exists()
    all_text = "\n".join(
        path.read_text(encoding="utf-8") for path in output.rglob("*") if path.is_file()
    )
    assert "[[Beads/ga-zbmk|Bead ga-zbmk]]" in all_text
    assert "Sensitive title off by default" not in all_text
    assert "Sensitive description off by default" not in all_text
    assert "lookmanbenali@gmail.com" not in all_text
    assert "gc.branch" in all_text

    gate = obsidian_vault.gate_vault(
        output,
        phase="closeout",
        expected_source_digest=snapshot["source_digest"],
        expected_work_authority="beads",
    )
    assert gate["ok"] is True
    assert gate["status"] == "passed"
    assert gate["gate"] == "obsidian-closeout"

    wrong_authority = obsidian_vault.gate_vault(
        output,
        phase="closeout",
        expected_source_digest=snapshot["source_digest"],
        expected_work_authority="taskmaster",
    )
    assert wrong_authority["ok"] is False
    assert wrong_authority["status"] == "blocked"
    assert "vault work authority drift" in wrong_authority["problems"][0]

    stale = obsidian_vault.gate_vault(
        output,
        phase="closeout",
        expected_source_digest="0" * 64,
        expected_work_authority="beads",
    )
    assert stale["ok"] is False
    assert stale["status"] == "blocked"
    assert "vault source digest is stale" in stale["problems"]


def test_gate_blocks_missing_or_empty_declared_work_projection(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    missing = obsidian_vault.gate_vault(
        tmp_path / "missing-vault",
        phase="readiness",
        expected_source_digest="0" * 64,
        expected_work_authority="beads",
    )
    assert missing["ok"] is False
    assert missing["status"] == "blocked"
    assert "vault directory is missing or is a symlink" in missing["problems"]

    source = tmp_path / "empty-beads.json"
    source.write_text("[]\n", encoding="utf-8")
    snapshot = obsidian_vault.collect_snapshot(root, [], bead_snapshot=source)
    output = tmp_path / "empty-vault"
    obsidian_vault.build_vault(snapshot, output, target_dir=root)
    empty = obsidian_vault.gate_vault(
        output,
        phase="closeout",
        expected_source_digest=snapshot["source_digest"],
        expected_work_authority="beads",
    )
    assert empty["ok"] is False
    assert empty["status"] == "blocked"
    assert "vault contains no projected work items" in empty["problems"]


def test_cli_gate_uses_same_explicit_bead_snapshot_as_build(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path)
    source = _bead_snapshot(tmp_path / "beads.json")
    output = tmp_path / "cli-bead-vault"
    common = [
        "--source-root",
        str(SOURCE_ROOT),
        "vault",
    ]
    assert aegis_cli.main(
        [
            *common,
            "build",
            "--target-dir",
            str(root),
            "--output",
            str(output),
            "--beads-json",
            str(source),
        ]
    ) == 0
    built = json.loads(capsys.readouterr().out)
    assert built["work_authority"] == "beads"

    assert aegis_cli.main(
        [
            *common,
            "gate",
            "--phase",
            "readiness",
            "--target-dir",
            str(root),
            "--output",
            str(output),
            "--beads-json",
            str(source),
        ]
    ) == 0
    gated = json.loads(capsys.readouterr().out)
    assert gated["ok"] is True
    assert gated["gate"] == "obsidian-readiness"


def test_identity_projection_holds_busy_per_bead_projects() -> None:
    # 2026-10-19: per-bead worktrees gave blog 547 sessions, over the old
    # 500 ceiling, which froze its vault projection.
    events = [
        {"session_id": f"s-{n}", "branch": f"codex/b-{n}", "worktree": f"/w/b-{n}"}
        for n in range(600)
    ]
    records = obsidian_vault._identity_records(events, obsidian_vault.VaultLimits())
    assert len(records) == 600


def test_identity_projection_still_bounded_by_edge_ceiling() -> None:
    limits = obsidian_vault.VaultLimits()
    events = [
        {"session_id": f"s-{n}"} for n in range(limits.max_identity_edges + 1)
    ]
    with pytest.raises(obsidian_vault.VaultError, match="edge limit"):
        obsidian_vault._identity_records(events, limits)
