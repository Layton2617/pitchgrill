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
                "PDF support needs pypdf (pip install pypdf), "
                "or convert the deck to .txt first."
            )
        reader = pypdf.PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pitchgrill", description="Get grilled before the VCs do")
    p.add_argument("--deck", required=True, help="path to the deck (.txt or .pdf)")
    p.add_argument("--stage", required=True, help="round, e.g. pre-seed / seed / series-a")
    p.add_argument("--sector", default=None, help="sector, e.g. saas / marketplace")
    p.add_argument("--wedge", default="general", choices=WEDGES)
    p.add_argument("--founder", default=None, help="path to an optional founder note")
    p.add_argument("--model", default=engine.MODEL, help="override the default model id")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    deck_path = Path(args.deck)
    if not deck_path.exists():
        sys.exit(f"deck not found: {deck_path}")
    deck = _read_deck(deck_path)

    founder = ""
    if args.founder:
        fp = Path(args.founder)
        if not fp.exists():
            sys.exit(f"founder note not found: {fp}")
        founder = fp.read_text(encoding="utf-8")

    loaded = kb.load_kb()
    if loaded.is_empty:
        print(
            "[warn] knowledge base is empty. Build it first: "
            "`python scripts/explode_kb.py <kb.json>`.",
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
