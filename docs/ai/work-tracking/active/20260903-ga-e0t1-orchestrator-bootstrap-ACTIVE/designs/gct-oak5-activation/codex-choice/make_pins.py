"""Derive pins.json for the codex-choice activation from the live city.toml (read-only).

  python3 -I -B make_pins.py <out pins.json>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import activate_codex as a  # noqa: E402

CITY = Path("/home/loucmane/gascity/city")
CANDIDATE_ROOT = "/home/loucmane/gas-city-template-candidate-worktrees"
# The live city.toml after the gct-oak5 Template lane activation (r1 city step), adopted by M11.
CITY_BEFORE = "b0eeb168579f3e247cafa634af3e74d0eb8d57109c21f71f9b2bfa035cecf47b"


def main(out):
    raw = (CITY / "city.toml").read_bytes()
    a.require(a.digest(raw) == CITY_BEFORE, "live city.toml is not the M11-adopted predecessor")
    pins = dict(
        city=str(CITY), candidate_root=CANDIDATE_ROOT, gc="/home/loucmane/gascity/bin/gc", uid=1000,
        env={"PATH": "/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin", "HOME": "/home/loucmane",
             "LANG": "C", "GC_HOME": "/home/loucmane/gascity/home", "GIT_OPTIONAL_LOCKS": "0",
             "BD_DISABLE_METRICS": "1"},
        city_before=CITY_BEFORE,
        inputs={a.CITY_NAME: a.digest(a.new_city(raw, CANDIDATE_ROOT))},
        executor=a.executor_digests(),
    )
    data = (json.dumps(pins, indent=1, sort_keys=True) + "\n").encode()
    Path(out).write_bytes(data)
    print(json.dumps(dict(pins_sha256=a.digest(data), inputs=pins["inputs"]), indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
