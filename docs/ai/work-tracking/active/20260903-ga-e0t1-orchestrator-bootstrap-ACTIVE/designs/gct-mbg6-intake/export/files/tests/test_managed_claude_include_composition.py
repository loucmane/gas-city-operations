"""Managed grants must survive include composition, not just render.

Live canary ga-vh6 (2026-08-22) proved that a conformant fragment is not a
working grant. `gc` folds an included fragment into the root `city.toml` with
a per-field provider merge that carries only a fixed set of scalar and slice
fields; `options_schema`, `option_defaults` and `base` are never among them.
A provider the root already declares therefore keeps the root's schema and
silently discards the generated one, while `[[patches.agent]]` from the same
fragment still applies. Session ci-8yxb launched with the reviewed model flag
and no `--add-dir` grant at all.

These tests compose the real live shape — this repository's own reviewed root
Claude schema plus the generated fragment — and assert the argv `gc` would
hand the implementation worker.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tomllib
from typing import Any

import pytest

from conftest import CoreBuildEnvironment


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "gct-managed-rig-permissions"
REVIEWED_CITY = ROOT / "city.toml"
WORKER = "gc.implementation-worker"

# gc resolves a `base = "provider:x"` chain at config load, so a fragment may
# safely introduce a provider the root never names. It may not extend one the
# root already declares: config.deepMergeProvider carries only these fragment
# fields onto an existing provider and leaves everything else — options_schema
# included — at the root's value, without a warning.
FRAGMENT_FIELDS_THAT_SURVIVE_A_ROOT_PROVIDER = frozenset(
    {
        "accept_startup_dialogs",
        "args",
        "command",
        "display_name",
        "emits_permission_warning",
        "env",
        "process_names",
        "prompt_flag",
        "prompt_mode",
        "ready_delay_ms",
        "ready_prompt_prefix",
        "upstream_env",
    }
)


def _compose_providers(root: dict[str, Any], fragment: dict[str, Any]) -> dict[str, Any]:
    """Compose fragment providers onto the root the way `gc` does."""
    providers = {
        name: dict(spec) for name, spec in root.get("providers", {}).items()
    }
    for name, spec in fragment.get("providers", {}).items():
        if name not in providers:
            providers[name] = dict(spec)
            continue
        surviving = {
            key: value
            for key, value in spec.items()
            if key in FRAGMENT_FIELDS_THAT_SURVIVE_A_ROOT_PROVIDER
        }
        providers[name] = {**providers[name], **surviving}
    return providers


def _merge_choices_by_value(
    inherited: list[dict[str, Any]], own: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged = list(inherited)
    index = {choice["value"]: position for position, choice in enumerate(merged)}
    for choice in own:
        position = index.get(choice["value"])
        if position is None:
            index[choice["value"]] = len(merged)
            merged.append(choice)
        else:
            merged[position] = choice
    return merged


def _merge_options_by_key(
    inherited: list[dict[str, Any]], own: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged = [dict(option) for option in inherited]
    index = {option["key"]: position for position, option in enumerate(merged)}
    for option in own:
        position = index.get(option["key"])
        if position is None:
            index[option["key"]] = len(merged)
            merged.append(dict(option))
            continue
        combined = {**merged[position], **option}
        combined["choices"] = _merge_choices_by_value(
            merged[position].get("choices", []), option.get("choices", [])
        )
        merged[position] = combined
    return merged


def _effective_options_schema(
    providers: dict[str, Any], name: str
) -> list[dict[str, Any]]:
    """Resolve one provider's schema through its `provider:` inheritance chain."""
    spec = providers[name]
    own = spec.get("options_schema")
    base = spec.get("base", "")
    if not base.startswith("provider:"):
        return list(own or [])
    inherited = _effective_options_schema(providers, base[len("provider:") :])
    if own is None:
        return inherited
    if spec.get("options_schema_merge") == "by_key":
        return _merge_options_by_key(inherited, own)
    return list(own)


def _render_argv(
    schema: list[dict[str, Any]], option_defaults: dict[str, str]
) -> list[str]:
    """Emit the extra argv `gc` builds from a schema and an agent's defaults."""
    argv: list[str] = []
    for option in schema:
        value = option_defaults.get(option["key"]) or option.get("default", "")
        if not value:
            continue
        choice = next(
            (item for item in option.get("choices", []) if item["value"] == value),
            None,
        )
        if choice is None:
            # gc walks the schema, not the defaults, so a selection whose
            # option did not survive contributes nothing and raises nothing.
            continue
        argv.extend(choice.get("flag_args", []))
    return argv


def _add_dir_grants(argv: list[str]) -> list[str]:
    return [
        argv[position + 1]
        for position, argument in enumerate(argv)
        if argument == "--add-dir"
    ]


def _agent_patch(fragment: dict[str, Any], rig: str, agent: str) -> dict[str, Any]:
    return next(
        patch
        for patch in fragment.get("patches", {}).get("agent", [])
        if patch["dir"] == rig and patch["name"] == agent
    )


def _fixture_rig(tmp_path: Path, name: str) -> tuple[Path, Path, dict[str, Any]]:
    repository = tmp_path / "repositories" / name
    worktree_root = tmp_path / "worktrees" / name
    (repository / ".git").mkdir(parents=True)
    worktree_root.mkdir(parents=True)
    return (
        repository,
        worktree_root,
        {
            "name": name,
            "repository_path": str(repository),
            "worktree_root": str(worktree_root),
            "agents": [WORKER],
            "git_metadata": True,
            "provider": "claude",
        },
    )


def _reviewed_city(tmp_path: Path, *extra: str) -> Path:
    """Stage the published root city.toml — the shape the live city runs."""
    city = tmp_path / "city"
    city.mkdir(exist_ok=True)
    destination = city / "city.toml"
    shutil.copyfile(REVIEWED_CITY, destination)
    if extra:
        destination.write_text(
            destination.read_text(encoding="utf-8") + "\n" + "\n".join(extra),
            encoding="utf-8",
        )
    return city


def _write_registry(
    path: Path,
    rigs: list[dict[str, Any]],
    *,
    schema: str = "gc.managed-rig-permissions.v1",
) -> None:
    vault = path.parent / "classified-vault"
    vault.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": schema,
                "classified_vault": str(vault),
                "rigs": rigs,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _provision(
    tmp_path: Path, city: Path, registry: Path, *arguments: str
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["GCT_TEST_ROOT"] = str(tmp_path.resolve())
    environment["GCT_SKIP_CONFIG_VALIDATION"] = "1"
    return subprocess.run(
        [
            str(TOOL),
            "--city",
            str(city),
            "--registry",
            str(registry),
            "--json",
            *arguments,
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _load(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def test_composed_live_shape_grants_the_worker_its_worktree_and_git_roots(
    tmp_path: Path,
) -> None:
    repository, worktree_root, record = _fixture_rig(tmp_path, "gas-city-template")
    city = _reviewed_city(tmp_path)
    registry = tmp_path / "registry.json"
    _write_registry(registry, [record])

    result = _provision(tmp_path, city, registry, "--apply")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["state"] == "conformant"

    fragment = _load(city / "managed" / "rig-permissions.toml")
    providers = _compose_providers(_load(city / "city.toml"), fragment)
    patch = _agent_patch(fragment, "gas-city-template", WORKER)
    schema = _effective_options_schema(providers, patch.get("provider", "claude"))
    argv = _render_argv(schema, patch["option_defaults"])

    assert _add_dir_grants(argv) == [
        str(worktree_root),
        str(repository / ".git"),
    ]
    assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
    assert "--dangerously-skip-permissions" not in argv
    assert str(repository) not in _add_dir_grants(argv)


def test_composed_live_shape_keeps_the_reviewed_model_picker_selectable(
    tmp_path: Path,
) -> None:
    _, _, record = _fixture_rig(tmp_path, "gas-city-template")
    city = _reviewed_city(tmp_path)
    registry = tmp_path / "registry.json"
    _write_registry(registry, [record])

    assert _provision(tmp_path, city, registry, "--apply").returncode == 0

    fragment = _load(city / "managed" / "rig-permissions.toml")
    providers = _compose_providers(_load(city / "city.toml"), fragment)
    patch = _agent_patch(fragment, "gas-city-template", WORKER)
    schema = _effective_options_schema(providers, patch.get("provider", "claude"))

    model = next(option for option in schema if option["key"] == "model")
    assert [choice["value"] for choice in model["choices"]] == [
        "opus-5-5",
        "fable-5",
        "haiku-4-5",
        "sonnet-5",
    ]


def test_rendered_patch_selects_the_provider_that_carries_the_grant(
    tmp_path: Path,
) -> None:
    """The two halves must name each other, not merely both exist."""
    _, _, record = _fixture_rig(tmp_path, "gas-city-template")
    city = _reviewed_city(tmp_path)
    registry = tmp_path / "registry.json"
    _write_registry(registry, [record])

    assert _provision(tmp_path, city, registry, "--apply").returncode == 0

    fragment = _load(city / "managed" / "rig-permissions.toml")
    patch = _agent_patch(fragment, "gas-city-template", WORKER)
    selected = patch["option_defaults"]["managed_worktree_access"]
    schema = fragment["providers"][patch["provider"]]["options_schema"]
    option = next(
        item for item in schema if item["key"] == "managed_worktree_access"
    )
    choice = next(item for item in option["choices"] if item["value"] == selected)
    assert choice["flag_args"][0] == "--add-dir"


def test_apply_refuses_when_the_root_city_swallows_the_managed_claude_schema(
    tmp_path: Path,
) -> None:
    _, _, record = _fixture_rig(tmp_path, "gas-city-template")
    city = _reviewed_city(
        tmp_path,
        "[providers.claude-managed]",
        'base = "provider:claude"',
        "",
        "[[providers.claude-managed.options_schema]]",
        'key = "managed_worktree_access"',
        'label = "Operator override"',
        'type = "select"',
        'default = "none"',
        "",
        "[[providers.claude-managed.options_schema.choices]]",
        'value = "none"',
        "flag_args = []",
        "",
    )
    registry = tmp_path / "registry.json"
    _write_registry(registry, [record])
    output = city / "managed" / "rig-permissions.toml"
    output.parent.mkdir(parents=True)
    output.write_text("# evidence\n", encoding="utf-8")
    before = output.read_bytes()

    result = _provision(tmp_path, city, registry, "--apply")

    assert result.returncode == 3
    assert "composed city" in result.stderr
    assert output.read_bytes() == before


def test_native_gc_composes_the_fragment_the_way_these_tests_model_it(
    tmp_path: Path,
    core_build_environment: CoreBuildEnvironment,
) -> None:
    """Pin the composition model to the tool that actually launches workers.

    Everything above reasons about `gc`'s include precedence from Python. This
    test hands the same two files to native `gc` and requires that its resolved
    providers match, so the model cannot quietly drift away from the mechanism
    that dropped the schema in the first place.
    """
    gc = _build_reviewed_gc(tmp_path, core_build_environment)
    repository, worktree_root, record = _fixture_rig(tmp_path, "gas-city-template")
    record["agents"] = ["implementation-worker"]
    city = tmp_path / "city"
    city.mkdir()
    (city / "city.toml").write_text(
        "\n".join(
            [
                'include = ["managed/rig-permissions.toml"]',
                "",
                "[workspace]",
                'provider = "claude"',
                "",
                "[providers.claude]",
                'base = "builtin:claude"',
                'options_schema_merge = "by_key"',
                'option_defaults = { model = "opus-5-5", permission_mode = "auto-edit" }',
                "",
                "[[providers.claude.options_schema]]",
                'key = "model"',
                'label = "Model"',
                'type = "select"',
                'default = "opus-5-5"',
                "",
                "[[providers.claude.options_schema.choices]]",
                'value = "opus-5-5"',
                'label = "Claude Opus 5.5"',
                'flag_args = ["--model", "claude-opus-5-5"]',
                "",
                "[[agent]]",
                'dir = "gas-city-template"',
                'name = "implementation-worker"',
                'provider = "claude"',
                "",
                "[[rigs]]",
                'name = "gas-city-template"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    site = city / ".gc"
    site.mkdir()
    (site / "site.toml").write_text(
        "\n".join(
            [
                "[[rig]]",
                'name = "gas-city-template"',
                f'path = "{repository}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    registry = tmp_path / "registry.json"
    _write_registry(registry, [record])
    assert _provision(tmp_path, city, registry, "--apply").returncode == 0

    resolved = subprocess.run(
        [str(gc), "--city", str(city), "config", "show"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
        env=core_build_environment.apply(),
    )
    assert resolved.returncode == 0, resolved.stderr
    composed = tomllib.loads(resolved.stdout)

    fragment = _load(city / "managed" / "rig-permissions.toml")
    modelled = _compose_providers(_load(city / "city.toml"), fragment)
    managed = _agent_patch(fragment, "gas-city-template", "implementation-worker")[
        "provider"
    ]

    for name in ("claude", managed):
        assert (
            composed["providers"][name]["options_schema"]
            == modelled[name]["options_schema"]
        ), name

    worker = next(
        agent
        for agent in composed["agent"]
        if agent.get("dir") == "gas-city-template"
        and agent["name"] == "implementation-worker"
    )
    assert worker["provider"] == managed
    schema = _effective_options_schema(composed["providers"], managed)
    argv = _render_argv(schema, worker["option_defaults"])
    assert _add_dir_grants(argv) == [str(worktree_root), str(repository / ".git")]


def _build_reviewed_gc(
    tmp_path: Path, core_build_environment: CoreBuildEnvironment
) -> Path:
    from test_managed_worker_canary_provisioning import _run_owned_phase

    core_source = Path(os.environ.get("GCT_CORE_SOURCE", ""))
    core_commit = os.environ.get("GCT_CORE_COMMIT", "")
    assert core_source.is_absolute() and core_source.is_dir()
    assert len(core_commit) == 40 and all(c in "0123456789abcdef" for c in core_commit)
    archive = tmp_path / "reviewed-core.tar"
    environment = core_build_environment.apply()
    archived = _run_owned_phase(
        name="archive-reviewed-core",
        argv=[
            "/usr/bin/git",
            "-C",
            str(core_source),
            "archive",
            "--format=tar",
            f"--output={archive}",
            core_commit,
        ],
        cwd=tmp_path,
        environment=environment,
        timeout=30,
        evidence_path=tmp_path / "reviewed-core-phases/archive.json",
    )
    assert archived["exit_code"] == 0 and not archived["timed_out"], archived
    core = tmp_path / "reviewed-core"
    core.mkdir()
    with tarfile.open(archive) as stream:
        stream.extractall(core, filter="data")
    go = shutil.which("go")
    assert go is not None, "the pinned managed-worker Go toolchain is required"
    binary = tmp_path / "reviewed-core-gc"
    built = _run_owned_phase(
        name="build-reviewed-core-gc",
        argv=[go, "build", "-buildvcs=false", "-o", str(binary), "./cmd/gc"],
        cwd=core,
        environment=environment,
        timeout=360,
        evidence_path=tmp_path / "reviewed-core-phases/build.json",
    )
    assert built["exit_code"] == 0 and not built["timed_out"], built
    assert binary.is_file() and os.access(binary, os.X_OK)
    return binary


def test_native_gc_composes_the_dedicated_claude_signing_provider(
    tmp_path: Path,
    core_build_environment: CoreBuildEnvironment,
) -> None:
    gc = _build_reviewed_gc(tmp_path, core_build_environment)
    repository, worktree_root, record = _fixture_rig(tmp_path, "gascity")
    record["agents"] = ["implementation-worker"]
    record["control_policy"] = {
        "source": "templates/claude/core-signing-control-policy.json",
        "sha256": hashlib.sha256(
            (ROOT / "templates/claude/core-signing-control-policy.json").read_bytes()
        ).hexdigest(),
    }
    executable = tmp_path / "python"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    record["environment"] = {"PATH": "/usr/bin:/bin"}
    record["toolchains"] = [
        {
            "name": "python",
            "executable": {
                "path": str(executable),
                "resolved_path": str(executable),
                "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "version_args": ["--version"],
                "version": "fixture-python",
            },
        }
    ]
    city = tmp_path / "city"
    city.mkdir()
    (city / "city.toml").write_text(
        "\n".join(
            [
                'include = ["managed/rig-permissions.toml"]',
                "",
                "[workspace]",
                'provider = "claude"',
                "",
                "[providers.claude]",
                'base = "builtin:claude"',
                'options_schema_merge = "by_key"',
                'option_defaults = { model = "opus-5-5", permission_mode = "auto-edit" }',
                "",
                "[[providers.claude.options_schema]]",
                'key = "model"',
                'label = "Model"',
                'type = "select"',
                'default = "opus-5-5"',
                "",
                "[[providers.claude.options_schema.choices]]",
                'value = "opus-5-5"',
                'label = "Claude Opus 5.5"',
                'flag_args = ["--model", "claude-opus-5-5"]',
                "",
                "[[agent]]",
                'dir = "gascity"',
                'name = "implementation-worker"',
                'provider = "claude"',
                "",
                "[[rigs]]",
                'name = "gascity"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    site = city / ".gc"
    site.mkdir()
    (site / "site.toml").write_text(
        "\n".join(
            [
                "[[rig]]",
                'name = "gascity"',
                f'path = "{repository}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    registry = tmp_path / "registry.json"
    _write_registry(
        registry,
        [record],
        schema="gc.managed-rig-permissions.v2",
    )
    assert _provision(tmp_path, city, registry, "--apply").returncode == 0

    resolved = subprocess.run(
        [str(gc), "--city", str(city), "config", "show"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
        env=core_build_environment.apply(),
    )
    assert resolved.returncode == 0, resolved.stderr
    composed = tomllib.loads(resolved.stdout)
    worker = next(
        agent
        for agent in composed["agent"]
        if agent.get("dir") == "gascity" and agent["name"] == "implementation-worker"
    )
    assert worker["provider"] == "claude-signing"
    signing = composed["providers"]["claude-signing"]
    assert signing["command"] == (
        "/home/loucmane/gas-city-template/bin/gct-claude-signing-worker"
    )
    assert signing["resume_command"].endswith("--resume {{.SessionKey}}")
    schema = _effective_options_schema(composed["providers"], "claude-signing")
    argv = _render_argv(schema, worker["option_defaults"])
    policy = str(
        (ROOT / "templates/claude/core-signing-control-policy.json").resolve()
    )
    assert argv.count(policy) == 1
    assert _add_dir_grants(argv) == [str(worktree_root), str(repository / ".git")]
    assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
    assert argv[argv.index("--permission-mode") + 1] == "dontAsk"
    assert argv[argv.index("--effort") + 1] == "max"
    assert "--dangerously-skip-permissions" not in argv


def _candidate_composition_city(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Stage the Operations candidate record, city and v2 registry the composition tests share."""
    repository, worktree_root, record = _fixture_rig(tmp_path, "gascity")
    record["agents"] = ["operations-candidate-worker"]
    record["git_metadata"] = False
    record["control_policy"] = {
        "source": "templates/claude/candidate-control-policy.json",
        "sha256": hashlib.sha256(
            (ROOT / "templates/claude/candidate-control-policy.json").read_bytes()
        ).hexdigest(),
    }
    # The v2 schema, required for git_metadata false, also requires both.
    executable = tmp_path / "python"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    record["environment"] = {"PATH": "/usr/bin:/bin"}
    record["toolchains"] = [
        {
            "name": "python",
            "executable": {
                "path": str(executable),
                "resolved_path": str(executable),
                "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "version_args": ["--version"],
                "version": "fixture-python",
            },
        }
    ]
    city = tmp_path / "city"
    city.mkdir()
    (city / "city.toml").write_text(
        "\n".join(
            [
                'include = ["managed/rig-permissions.toml"]',
                "",
                "[workspace]",
                'provider = "claude"',
                "",
                "[providers.claude]",
                'base = "builtin:claude"',
                'options_schema_merge = "by_key"',
                'option_defaults = { model = "opus-5-5", permission_mode = "auto-edit" }',
                "",
                "[[providers.claude.options_schema]]",
                'key = "model"',
                'label = "Model"',
                'type = "select"',
                'default = "opus-5-5"',
                "",
                "[[providers.claude.options_schema.choices]]",
                'value = "opus-5-5"',
                'label = "Claude Opus 5.5"',
                'flag_args = ["--model", "claude-opus-5-5"]',
                "",
                "[[agent]]",
                'dir = "gascity"',
                'name = "operations-candidate-worker"',
                'provider = "claude"',
                "",
                "[[rigs]]",
                'name = "gascity"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    site = city / ".gc"
    site.mkdir()
    (site / "site.toml").write_text(
        "\n".join(
            [
                "[[rig]]",
                'name = "gascity"',
                f'path = "{repository}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    registry = tmp_path / "registry.json"
    _write_registry(
        registry,
        [record],
        schema="gc.managed-rig-permissions.v2",
    )
    return repository, worktree_root, city, registry


def test_candidate_composition_fixture_renders_without_core(tmp_path: Path) -> None:
    """The record the native-gc test composes is a valid v2 record the renderer applies.

    The native test needs the CI-built Core, so a registry refusal there would hide
    behind the missing-Core failure locally; this runs the real renderer on the
    same staged record without Core.
    """
    _, worktree_root, city, registry = _candidate_composition_city(tmp_path)
    result = _provision(tmp_path, city, registry, "--apply")
    assert result.returncode == 0, result.stderr
    fragment = tomllib.loads((city / "managed" / "rig-permissions.toml").read_text(encoding="utf-8"))
    assert "claude-candidate" in fragment["providers"]
    assert "claude-managed" not in fragment["providers"]
    (patch,) = fragment["patches"]["agent"]
    assert patch["provider"] == "claude-candidate"
    assert patch["option_defaults"]["permission_mode"] == "full-auto"


def test_native_gc_composes_the_dedicated_claude_candidate_provider(
    tmp_path: Path,
    core_build_environment: CoreBuildEnvironment,
) -> None:
    """A candidate-kind record launches through the closed candidate wrapper.

    The generic claude-managed launch also loads the city's shared settings,
    whose broader grant would union with the candidate policy; the dedicated
    provider's wrapper removes it, exactly as the signing provider does.
    """
    gc = _build_reviewed_gc(tmp_path, core_build_environment)
    repository, worktree_root, city, registry = _candidate_composition_city(tmp_path)
    assert _provision(tmp_path, city, registry, "--apply").returncode == 0

    resolved = subprocess.run(
        [str(gc), "--city", str(city), "config", "show"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
        env=core_build_environment.apply(),
    )
    assert resolved.returncode == 0, resolved.stderr
    composed = tomllib.loads(resolved.stdout)
    worker = next(
        agent
        for agent in composed["agent"]
        if agent.get("dir") == "gascity"
        and agent["name"] == "operations-candidate-worker"
    )
    assert worker["provider"] == "claude-candidate"
    candidate = composed["providers"]["claude-candidate"]
    assert candidate["command"] == (
        "/home/loucmane/gas-city-template/bin/gct-claude-candidate-worker"
    )
    assert candidate["resume_command"].endswith("--resume {{.SessionKey}}")
    schema = _effective_options_schema(composed["providers"], "claude-candidate")
    argv = _render_argv(schema, worker["option_defaults"])
    policy = str((ROOT / "templates/claude/candidate-control-policy.json").resolve())
    assert argv.count(policy) == 1
    assert _add_dir_grants(argv) == [str(worktree_root)]
    assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
    assert argv[argv.index("--permission-mode") + 1] == "dontAsk"
    assert argv[argv.index("--effort") + 1] == "max"
    assert "--dangerously-skip-permissions" not in argv


def _template_pack_composition_city(
    root: Path, *, surviving_override: bool
) -> tuple[Path, Path, Path, Path]:
    """Stage the Template record in the same imported-pack shape as the live rig."""

    repository, worktree_root, record = _fixture_rig(root, "gas-city-template")
    record["agents"] = ["implementation-worker"]
    record["git_metadata"] = False
    record["control_policy"] = {
        "source": "templates/claude/template-candidate-control-policy.json",
        "sha256": hashlib.sha256(
            (ROOT / "templates/claude/template-candidate-control-policy.json").read_bytes()
        ).hexdigest(),
    }
    executable = root / "python"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    record["environment"] = {"PATH": "/usr/bin:/bin"}
    record["toolchains"] = [
        {
            "name": "python",
            "executable": {
                "path": str(executable),
                "resolved_path": str(executable),
                "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "version_args": ["--version"],
                "version": "fixture-python",
            },
        }
    ]

    city = root / "city"
    pack = city / "packs/gc"
    pack.mkdir(parents=True)
    (pack / "pack.toml").write_text(
        "\n".join(
            [
                "[pack]",
                'name = "gc"',
                "schema = 2",
                "",
                "[[agent]]",
                'name = "implementation-worker"',
                'scope = "rig"',
                'provider = "claude"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    root_lines = [
        'include = ["managed/rig-permissions.toml"]',
        "",
        "[workspace]",
        'provider = "claude"',
        "",
        "[providers.claude]",
        'base = "builtin:claude"',
        'options_schema_merge = "by_key"',
        'option_defaults = { model = "opus-5-5", permission_mode = "auto-edit", worktree_access = "none" }',
        "",
        "[[providers.claude.options_schema]]",
        'key = "model"',
        'label = "Model"',
        'type = "select"',
        'default = "opus-5-5"',
        "",
        "[[providers.claude.options_schema.choices]]",
        'value = "opus-5-5"',
        'label = "Claude Opus 5.5"',
        'flag_args = ["--model", "claude-opus-5-5"]',
        "",
        "[[providers.claude.options_schema]]",
        'key = "permission_mode"',
        'label = "Permission Mode"',
        'type = "select"',
        'default = "auto-edit"',
        "",
        "[[providers.claude.options_schema.choices]]",
        'value = "auto-edit"',
        'label = "Auto edit"',
        'flag_args = ["--permission-mode", "auto"]',
        "",
        "[[providers.claude.options_schema]]",
        'key = "worktree_access"',
        'label = "Worktree access"',
        'type = "select"',
        'default = "none"',
        "",
        "[[providers.claude.options_schema.choices]]",
        'value = "none"',
        'label = "Current workdir only"',
        "flag_args = []",
        "",
        "[[providers.claude.options_schema.choices]]",
        'value = "template-worktrees-and-git-metadata"',
        'label = "Template worktrees and Git metadata"',
        'flag_args = ["--add-dir", "/home/loucmane/gas-city-template-worktrees", "--add-dir", "/home/loucmane/gas-city-template/.git"]',
        "",
        "[[rigs]]",
        'name = "gas-city-template"',
        f'path = "{repository}"',
        "",
        "[rigs.imports.gc]",
        'source = "./packs/gc"',
        "",
    ]
    if surviving_override:
        root_lines.extend(
            [
                "[[rigs.overrides]]",
                'agent = "implementation-worker"',
                'provider = "claude"',
                'option_defaults = { permission_mode = "auto-edit", worktree_access = "template-worktrees-and-git-metadata" }',
                "",
            ]
        )
    (city / "city.toml").write_text("\n".join(root_lines), encoding="utf-8")
    registry = root / "registry.json"
    _write_registry(registry, [record], schema="gc.managed-rig-permissions.v2")
    return repository, worktree_root, city, registry


def test_native_pack_composition_exposes_the_surviving_template_override(
    tmp_path: Path,
    core_build_environment: CoreBuildEnvironment,
) -> None:
    """The live override silently restores generic Claude; its removal activates the lane."""

    gc = _build_reviewed_gc(tmp_path, core_build_environment)
    observed: dict[bool, tuple[dict[str, Any], dict[str, Any], Path]] = {}
    for surviving_override in (False, True):
        case = tmp_path / ("with-override" if surviving_override else "without-override")
        case.mkdir()
        _repository, worktree_root, city, registry = _template_pack_composition_city(
            case, surviving_override=surviving_override
        )
        provisioned = _provision(case, city, registry, "--apply")
        assert provisioned.returncode == 0, provisioned.stderr
        resolved = subprocess.run(
            [str(gc), "--city", str(city), "config", "show"],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
            env=core_build_environment.apply(),
        )
        assert resolved.returncode == 0, resolved.stderr
        composed = tomllib.loads(resolved.stdout)
        worker = next(
            agent
            for agent in composed["agent"]
            if agent.get("dir") == "gas-city-template"
            and agent["name"] == "implementation-worker"
        )
        observed[surviving_override] = (composed, worker, worktree_root)

    composed, worker, worktree_root = observed[False]
    assert worker["provider"] == "claude-template-candidate"
    assert worker["option_defaults"]["permission_mode"] == "full-auto"
    provider = composed["providers"]["claude-template-candidate"]
    assert provider["command"].endswith("/bin/gct-claude-template-candidate-worker")
    argv = _render_argv(
        _effective_options_schema(composed["providers"], worker["provider"]),
        worker["option_defaults"],
    )
    template_policy = str(
        (ROOT / "templates/claude/template-candidate-control-policy.json").resolve()
    )
    assert argv.count(template_policy) == 1
    assert _add_dir_grants(argv) == [str(worktree_root)]
    assert "/home/loucmane/gascity/city/.gc/settings.json" not in argv

    _composed, worker, _root = observed[True]
    assert worker["provider"] == "claude"
    assert worker["option_defaults"]["permission_mode"] == "auto-edit"
    assert (
        worker["option_defaults"]["worktree_access"]
        == "template-worktrees-and-git-metadata"
    )


def test_check_refuses_the_same_composition_it_would_refuse_to_apply(
    tmp_path: Path,
) -> None:
    _, _, record = _fixture_rig(tmp_path, "gas-city-template")
    city = _reviewed_city(
        tmp_path,
        "[providers.claude-managed]",
        'base = "provider:claude"',
        "",
        "[[providers.claude-managed.options_schema]]",
        'key = "managed_worktree_access"',
        'label = "Operator override"',
        'type = "select"',
        'default = "none"',
        "",
        "[[providers.claude-managed.options_schema.choices]]",
        'value = "none"',
        "flag_args = []",
        "",
    )
    registry = tmp_path / "registry.json"
    _write_registry(registry, [record])

    result = _provision(tmp_path, city, registry, "--check")

    assert result.returncode == 3
    assert "composed city" in result.stderr
    assert not (city / "managed" / "rig-permissions.toml").exists()


def test_apply_refuses_when_the_root_city_swallows_the_managed_codex_schema(
    tmp_path: Path,
) -> None:
    _, _, record = _fixture_rig(tmp_path, "hpfetcher")
    record.pop("provider")
    city = _reviewed_city(
        tmp_path,
        "[providers.codex]",
        'base = "builtin:codex"',
        "",
        "[[providers.codex.options_schema]]",
        'key = "worklog_access"',
        'label = "Operator override"',
        'type = "select"',
        'default = "none"',
        "",
        "[[providers.codex.options_schema.choices]]",
        'value = "none"',
        "flag_args = []",
        "",
    )
    registry = tmp_path / "registry.json"
    _write_registry(registry, [record])
    output = city / "managed" / "rig-permissions.toml"
    output.parent.mkdir(parents=True)
    output.write_text("# evidence\n", encoding="utf-8")
    before = output.read_bytes()

    result = _provision(tmp_path, city, registry, "--apply")

    assert result.returncode == 3
    assert "composed city" in result.stderr
    assert output.read_bytes() == before
