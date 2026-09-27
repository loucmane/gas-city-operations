"""Write image/pins.json from the reviewed inventory (inventory-data.json) and pin its digest in image_tool.py."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE.parent / "inventory-data.json").read_text())


def main():
    pins = {
        "skill_map": DATA["skill_map"],
        "owned_roots": DATA["catalog_value"]["OwnedRoots"],
        "catalog_value": DATA["catalog_value"],
        "ownership_sha256": DATA["ownership_bytes_sha256"],
    }
    assert sorted(e["Name"] for e in pins["catalog_value"]["Entries"]) == sorted(pins["skill_map"])
    raw = (json.dumps(pins, indent=1, sort_keys=True) + "\n").encode()
    (HERE / "pins.json").write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    tool = HERE / "image_tool.py"
    text = tool.read_text()
    new = re.sub(r"^PINS_SHA256 = '[0-9a-f]*'$", f"PINS_SHA256 = '{digest}'", text, count=1, flags=re.M)
    assert new.count(f"PINS_SHA256 = '{digest}'") == 1
    tool.write_text(new)
    print(digest)


if __name__ == "__main__":
    main()
