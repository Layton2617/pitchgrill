"""把一个 KB JSON 文件按 cell 落盘成 kb/<type 复数>/<cell>.yaml。

用法:python scripts/explode_kb.py <kb.json>
"""
import json
import re
import sys
from pathlib import Path

import yaml

TYPE_DIRS = {
    "red_flag": "red_flags",
    "grilling": "grilling",
    "data_room": "data_room",
    "deck_lint": "deck_lints",
    "benchmark": "benchmarks",
}

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_ROOT = REPO_ROOT / "kb"


def sanitize(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9._-]+", "_", name)
    return name.strip("_") or "unnamed"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    src = Path(argv[1])
    data = json.loads(src.read_text(encoding="utf-8"))

    cells = data.get("cells", [])
    written = 0
    skipped = []

    seen = {}  # (dir, filename) -> count, 防止 cell 名 sanitize 后撞车
    for cell in cells:
        ctype = cell.get("type")
        subdir = TYPE_DIRS.get(ctype)
        if subdir is None:
            skipped.append(cell.get("cell", "<no cell>"))
            continue

        items = cell.get("items") or []
        base = sanitize(cell.get("cell") or ctype)
        key = (subdir, base)
        seen[key] = seen.get(key, 0) + 1
        filename = base if seen[key] == 1 else f"{base}-{seen[key]}"

        out_dir = KB_ROOT / subdir
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "cell": cell.get("cell"),
            "type": ctype,
            "wedge": cell.get("wedge", "general"),
            "items": items,
        }
        (out_dir / f"{filename}.yaml").write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        written += 1

    print(f"wrote {written} cell files under {KB_ROOT}")
    if skipped:
        print(f"skipped {len(skipped)} cells with unknown type: {skipped}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
