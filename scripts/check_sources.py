"""校验 KB 里所有来源 URL 的存活,可选地剔除死链。

KB 由 LLM 生成,深链(带路径的文章 URL)约有 1-2 成是编错的 slug。阈值/实质内容
通常没问题,坏的是 URL 精确路径,所以这步只动 sources、不动条目本身。

用法:
    python scripts/check_sources.py kb_raw.json            # 只报告
    python scripts/check_sources.py kb_raw.json --strip    # 删掉死链并写回

存活判定:200/3xx/401/403/429 视为真实(403/429 多是站点拦爬虫);404/410 及
两次重试后仍连不通(000)视为死链。--strip 后记得重新 `explode_kb.py` 落盘。
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
    ap = argparse.ArgumentParser(description="校验 KB 来源 URL 存活")
    ap.add_argument("kb_json", help="KB JSON(含 cells[].items[].sources)")
    ap.add_argument("--strip", action="store_true", help="删掉死链并写回 JSON")
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
