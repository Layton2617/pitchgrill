"""Bundle the kb/ yaml into the web page.

Writes docs/kb.json (fallback) and inlines the KB into docs/index.html between the
/*KB_START*/.../*KB_END*/ markers, so the page needs no fetch and works offline.

Usage: python scripts/build_web.py
"""
import json
import re
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
    blob = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    n = sum(len(v) for v in out.values())

    dest = ROOT / "docs" / "kb.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(blob, encoding="utf-8")
    print(f"wrote {dest} ({n} items)")

    index = ROOT / "docs" / "index.html"
    html = index.read_text(encoding="utf-8")
    replacement = f"/*KB_START*/window.KB_INLINE={blob};/*KB_END*/"
    html2, count = re.subn(r"/\*KB_START\*/.*?/\*KB_END\*/", lambda _: replacement, html, flags=re.S)
    if count != 1:
        print(f"error: expected 1 KB marker block in index.html, found {count}", file=sys.stderr)
        return 1
    index.write_text(html2, encoding="utf-8")
    print(f"inlined KB into {index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
