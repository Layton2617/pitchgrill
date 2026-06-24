"""Check that every source URL in the KB is still live; optionally drop dead links.

Deep links (article URLs with a path) can have wrong slugs. Thresholds and substance are
usually fine; what breaks is the exact URL path, so this only touches `sources`, never the
items themselves.

Usage:
    python scripts/check_sources.py kb_raw.json            # report only
    python scripts/check_sources.py kb_raw.json --strip    # drop dead links, write back

Live: 200/3xx/401/403/429 (403/429 are usually bot-blocks, not dead). Dead: 404/410 and
anything still unreachable after a retry (000). After --strip, re-run explode_kb.py.
"""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

DEAD_CODES = {"404", "410", "000"}


def _collect_urls(data: dict) -> set:
    urls = set()
    for cell in data.get("cells", []):
        for item in cell.get("items") or []:
            for s in item.get("sources") or []:
                s = s.strip()
                if s.startswith("http"):
                    urls.add(s)
    return urls


def _check(url: str) -> tuple:
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L",
             "--retry", "1", "--max-time", "12", "-A", "Mozilla/5.0", url],
            capture_output=True, text=True, timeout=40,
        )
        return url, r.stdout.strip() or "000"
    except Exception:
        return url, "000"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check that KB source URLs are live")
    ap.add_argument("kb_json", help="KB JSON (with cells[].items[].sources)")
    ap.add_argument("--strip", action="store_true", help="drop dead links and write back")
    args = ap.parse_args(argv)

    data = json.loads(open(args.kb_json, encoding="utf-8").read())
    urls = sorted(_collect_urls(data))
    print(f"checking {len(urls)} distinct urls ...")

    status = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        for url, code in ex.map(_check, urls):
            status[url] = code

    from collections import Counter
    print("status:", dict(Counter(status.values())))
    dead = sorted(u for u, c in status.items() if c in DEAD_CODES)
    print(f"\ndead ({len(dead)}):")
    for u in dead:
        print(f"  {status[u]}  {u}")

    if not args.strip:
        return 1 if dead else 0

    dead_set = set(dead)
    removed = zeroed = 0
    for cell in data.get("cells", []):
        for item in cell.get("items") or []:
            srcs = item.get("sources")
            if not srcs:
                continue
            kept = [s for s in srcs if s.strip() not in dead_set]
            removed += len(srcs) - len(kept)
            if srcs and not kept:
                zeroed += 1
            item["sources"] = kept
    json.dump(data, open(args.kb_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nstripped {removed} dead links; {zeroed} items now have 0 sources.")
    print(f"wrote {args.kb_json} — re-run: python scripts/explode_kb.py {args.kb_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
