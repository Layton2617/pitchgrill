"""Bundle the kb/ yaml into docs/kb.json for the web page.

Usage: python scripts/build_web.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pitchgrill import kb as kb_mod  # noqa: E402


def main() -> int:
    kb = kb_mod.load_kb()
    out = {
        "red_flags": kb.red_flags,
        "grilling": kb.grilling,
        "data_room": kb.data_room,
        "deck_lints": kb.deck_lints,
        "benchmarks": kb.benchmarks,
    }
    dest = ROOT / "docs" / "kb.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {dest} ({sum(len(v) for v in out.values())} items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
