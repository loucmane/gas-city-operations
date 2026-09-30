"""Tests for the codex-choice activation (gct-oak5 handover prerequisite).

  python3 -m pytest -q designs/gct-oak5-activation/codex-choice/test_activate_codex.py

Pure tests on the live city.toml bytes (read-only) and a fixture Package whose gc calls are replaced.
"""
import json
from pathlib import Path
import sys
import tomllib

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import activate_codex as a  # noqa: E402

LIVE = Path("/home/loucmane/gascity/city/city.toml")
CAND = "/home/loucmane/gas-city-template-candidate-worktrees"


@pytest.fixture(scope="module")
def raw():
    data = LIVE.read_bytes()
    if a.digest(data) != json.loads((HERE / "pins.json").read_text())["city_before"]:
        pytest.skip("live city.toml moved past the pinned predecessor")
    return data


def test_postimage_is_the_pinned_input(raw):
    pins = json.loads((HERE / "pins.json").read_text())
    assert a.digest(a.new_city(raw, CAND)) == pins["inputs"]["city.toml"]
    assert pins["executor"] == a.executor_digests()
    assert pins["city_before"] == "b0eeb168579f3e247cafa634af3e74d0eb8d57109c21f71f9b2bfa035cecf47b"


def test_exactly_two_edits(raw):
    from collections import Counter
    old, new = Counter(raw.decode().splitlines()), Counter(a.new_city(raw, CAND).decode().splitlines())
    added, removed = sorted((new - old).elements()), sorted((old - new).elements())
    assert removed == ['work_dir_roots = ["/home/loucmane/gas-city-template-worktrees"]']
    assert added == sorted([
        '', '[[providers.codex.options_schema.choices]]',
        'value = "classified-vault-and-template-candidate-worktrees"',
        'label = "Classified GasCity vault and Template candidate worktrees"',
        'flag_args = ["--sandbox", "workspace-write", "-c", "sandbox_workspace_write.writable_roots=[\\"'
        '/home/loucmane/vaults/main/GasCity\\",\\"/home/loucmane/gas-city-template-candidate-worktrees\\"]"]',
        'work_dir_roots = ["/home/loucmane/gas-city-template-worktrees", '
        '"/home/loucmane/gas-city-template-candidate-worktrees"]'])
    assert sum(new.values()) == sum(old.values()) + 5


def test_new_choice_writes_no_git_metadata_and_default_is_unchanged(raw):
    cfg = tomllib.loads(a.new_city(raw, CAND).decode())
    choices = a.codex_choices(cfg)
    (choice,) = [c for c in choices if c["value"] == a.CHOICE]
    roots = json.loads(choice["flag_args"][3].split("=", 1)[1])
    assert roots == ["/home/loucmane/vaults/main/GasCity", CAND]
    assert not any(".git" in r for r in roots)
    assert choice["flag_args"][:3] == ["--sandbox", "workspace-write", "-c"] and len(choice["flag_args"]) == 4
    values = [c["value"] for c in choices]
    assert values.index(a.CHOICE) == values.index(a.ANCHOR) + 1
    (codex,) = [x for x in cfg["patches"]["agent"] if x.get("dir") == a.RIG and x.get("name") == "codex"
                and "option_defaults" in x]
    assert codex["option_defaults"] == {"worklog_access": a.DEFAULT}


@pytest.mark.parametrize("mutate", [
    lambda t: t.replace(a.ANCHOR_BLOCK, "", 1),
    lambda t: t.replace(a.PATCH_BEFORE, "", 1),
    lambda t: t + "\n" + a.ANCHOR_BLOCK,
    lambda t: t.replace(a.ANCHOR_BLOCK, a.ANCHOR_BLOCK + a.choice_block(CAND), 1),
])
def test_refuses_any_other_predecessor(raw, mutate):
    changed = mutate(raw.decode())
    assert changed != raw.decode()
    with pytest.raises((a.Refusal, ValueError, tomllib.TOMLDecodeError)):
        a.new_city(changed.encode(), CAND)


def test_unrelated_predecessor_drift_is_refused_by_the_pin(pkg, raw):
    """new_city tolerates edits elsewhere by design; the inputs step refuses them through the predecessor pin."""
    pkg.city_toml.write_bytes(raw.replace(b"max_active_sessions = 16", b"max_active_sessions = 17", 1))
    with pytest.raises(a.Refusal, match="city predecessor"):
        a.step_inputs(pkg)


def test_not_idempotent(raw):
    with pytest.raises(a.Refusal):
        a.new_city(a.new_city(raw, CAND), CAND)


class FakePackage(a.Package):
    def __init__(self, root, pins):
        self.root, self.pins = root, pins
        self.records, self.inputs = root / "records", root / "inputs"
        self.city = root / "city"
        self.city_toml = self.city / "city.toml"
        self.candidate_root = CAND
        self.gc, self.env, self.uid = "gc", {}, __import__("os").getuid()
        self.binding = dict(pins_sha256="x" * 64, executor_sha256="y" * 64)
        self.quiet_value = dict(controller=1, rigs=["gas-city-template"], suspension_sha256="z")

    def quiet(self):
        return dict(self.quiet_value)


@pytest.fixture
def pkg(tmp_path, raw, monkeypatch):
    (tmp_path / "city").mkdir()
    (tmp_path / "city" / "city.toml").write_bytes(raw)
    (tmp_path / "city" / "city.toml").chmod(0o644)
    (tmp_path / "records").mkdir(mode=0o700)
    (tmp_path / "inputs").mkdir(mode=0o700)
    pins = dict(city_before=a.digest(raw), inputs={"city.toml": a.digest(a.new_city(raw, CAND))})
    p = FakePackage(tmp_path, pins)
    agent = {"Provider": "codex", "OptionDefaults": {"worklog_access": a.DEFAULT}, "MaxActiveSessions": 1}

    def fake_agent(_p, city):
        text = (city / "city.toml").read_text()
        roots = [a.TEMPLATE_ROOT, CAND] if a.CHOICE in text else [a.TEMPLATE_ROOT]
        return dict(agent, WorkDirRoots=roots)

    monkeypatch.setattr(a, "codex_agent", fake_agent)
    monkeypatch.setattr(a, "validate_city", lambda _p, raw_: a.codex_proof(_p, dict(agent, WorkDirRoots=[a.TEMPLATE_ROOT, CAND]), [a.TEMPLATE_ROOT, CAND]))
    monkeypatch.setattr(a, "reload", lambda _p: dict(ok=True, outcome="applied", revision="r"))
    return p


def test_steps_apply_then_rollback(pkg, raw):
    a.step_inputs(pkg)
    a.step_city(pkg)
    assert a.sha(pkg.city_toml) == pkg.pins["inputs"]["city.toml"]
    a.step_reload(pkg)
    reload_record = json.loads(pkg.record("reload").read_text())
    assert reload_record["composed"]["WorkDirRoots"] == [a.TEMPLATE_ROOT, CAND]
    assert reload_record["choice"]["value"] == a.CHOICE
    with pytest.raises(a.Refusal, match="already consumed"):
        a.step_city(pkg)
    a.rollback(pkg)
    assert pkg.city_toml.read_bytes() == raw
    assert json.loads((pkg.records / "rollback.json").read_text())["actions"] == ["city.toml"]
    with pytest.raises(a.Refusal, match="rollback consumed"):
        a.step_reload(pkg)


def test_order_and_intent_guard(pkg):
    with pytest.raises(a.Refusal, match="earlier step missing"):
        a.step_city(pkg)
    a.step_inputs(pkg)
    pkg.intent("city", pkg.quiet())
    with pytest.raises(a.Refusal, match="use resume city"):
        a.step_city(pkg)


def test_resume_city_requires_postimage(pkg):
    a.step_inputs(pkg)
    pkg.intent("city", pkg.quiet())
    with pytest.raises(a.Refusal, match="reviewed postimage"):
        a.resume(pkg, "city")


def test_rollback_refuses_foreign_city(pkg):
    a.step_inputs(pkg)
    pkg.city_toml.write_text(pkg.city_toml.read_text() + "\n# foreign\n")
    with pytest.raises(a.Refusal, match="neither its predecessor nor its postimage"):
        a.rollback(pkg)


def test_quiet_drift_refuses(pkg):
    a.step_inputs(pkg)
    original = pkg.quiet_value
    calls = []

    def drifting():
        calls.append(1)
        return dict(original, controller=1 if len(calls) == 1 else 2)
    pkg.quiet = drifting
    with pytest.raises(a.Refusal, match="city changed during the step"):
        a.step_city(pkg)
