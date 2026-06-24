"""Command-line interface.

python check.py --deck path.{txt,pdf} --stage seed --sector saas --wedge ai-dev-tools
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import engine, kb, report

WEDGES = ["general", "cross-border-cn", "ai-dev-tools"]


def _read_deck(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            import pypdf
        except ImportError:
            sys.exit(
                "解析 PDF 需要 pypdf(pip install pypdf),"
                "或先把 deck 转成 .txt 再传入。"
            )
        reader = pypdf.PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pitchgrill", description="Get grilled before the VCs do")
    p.add_argument("--deck", required=True, help="deck 文件路径(.txt 或 .pdf)")
    p.add_argument("--stage", required=True, help="轮次,如 pre-seed / seed / series-a")
    p.add_argument("--sector", default=None, help="行业,如 saas / marketplace")
    p.add_argument("--wedge", default="general", choices=WEDGES)
    p.add_argument("--founder", default=None, help="创始人自述文件路径(可选)")
    p.add_argument("--model", default=engine.MODEL, help="覆盖默认模型 id")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    deck_path = Path(args.deck)
    if not deck_path.exists():
        sys.exit(f"找不到 deck 文件:{deck_path}")
    deck = _read_deck(deck_path)

    founder = ""
    if args.founder:
        fp = Path(args.founder)
        if not fp.exists():
            sys.exit(f"找不到自述文件:{fp}")
        founder = fp.read_text(encoding="utf-8")

    loaded = kb.load_kb()
    if loaded.is_empty:
        print(
            "[warn] KB 为空。请先运行 "
            "`python scripts/explode_kb.py <kb.json>` 落盘知识库。",
            file=sys.stderr,
        )

    result = engine.run(
        stage=args.stage,
        sector=args.sector,
        wedge=args.wedge,
        deck=deck,
        founder=founder,
        kb=loaded,
        model=args.model,
    )
    print(report.render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
