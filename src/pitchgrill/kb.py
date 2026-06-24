"""Load every yaml under kb/, build an in-memory index, and filter by dimension.

`general` wedge items apply to every wedge; passing a wedge stacks its niche items on top.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KB_ROOT = REPO_ROOT / "kb"

GENERAL = "general"

# type -> subdirectory on disk
TYPE_DIRS = {
    "red_flag": "red_flags",
    "grilling": "grilling",
    "data_room": "data_room",
    "deck_lint": "deck_lints",
    "benchmark": "benchmarks",
}


@dataclass
class KB:
    red_flags: list[dict] = field(default_factory=list)
    grilling: list[dict] = field(default_factory=list)
    data_room: list[dict] = field(default_factory=list)
    deck_lints: list[dict] = field(default_factory=list)
    benchmarks: list[dict] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(
            len(x)
            for x in (
                self.red_flags,
                self.grilling,
                self.data_room,
                self.deck_lints,
                self.benchmarks,
            )
        )

    @property
    def is_empty(self) -> bool:
        return self.total == 0


_BUCKET = {
    "red_flag": "red_flags",
    "grilling": "grilling",
    "data_room": "data_room",
    "deck_lint": "deck_lints",
    "benchmark": "benchmarks",
}


def load_kb(root: Path | None = None) -> KB:
    root = root or KB_ROOT
    kb = KB()
    if not root.exists():
        return kb

    for ctype, subdir in TYPE_DIRS.items():
        d = root / subdir
        if not d.exists():
            continue
        bucket = getattr(kb, _BUCKET[ctype])
        for yf in sorted(d.glob("*.yaml")):
            cell = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
            wedge = cell.get("wedge", GENERAL)
            for item in cell.get("items") or []:
                # benchmark items have no per-item wedge; inherit it from the cell
                item.setdefault("wedge", wedge)
                bucket.append(item)
    return kb


def _stage_match(item: dict, stage: str | None) -> bool:
    if stage is None:
        return True
    stages = item.get("stage")
    if not stages:  # no stage tag means it applies to all stages
        return True
    return stage in stages


def _wedge_match(item: dict, wedge: str | None) -> bool:
    iw = item.get("wedge", GENERAL)
    if iw == GENERAL:
        return True
    if wedge is None:
        return False
    return iw == wedge


def _sector_match(item: dict, sector: str | None) -> bool:
    isec = item.get("sector")
    if not isec:  # no sector tag means it applies to all sectors
        return True
    if not sector:  # sector-specific item, but no sector chosen
        return False
    return isec == sector


def _filter(items: list[dict], *, stage=None, wedge=None, sector=None, **exact) -> list[dict]:
    out = []
    for it in items:
        if not _stage_match(it, stage):
            continue
        if not _wedge_match(it, wedge):
            continue
        if not _sector_match(it, sector):
            continue
        if any(it.get(k) != v for k, v in exact.items() if v is not None):
            continue
        out.append(it)
    return out


def select_red_flags(kb: KB, *, stage=None, wedge=None, sector=None, domain=None) -> list[dict]:
    return _filter(kb.red_flags, stage=stage, wedge=wedge, sector=sector, domain=domain)


def select_grilling(kb: KB, *, stage=None, wedge=None, sector=None, theme=None) -> list[dict]:
    return _filter(kb.grilling, stage=stage, wedge=wedge, sector=sector, theme=theme)


def select_data_room(kb: KB, *, stage=None, wedge=None, sector=None, category=None) -> list[dict]:
    return _filter(kb.data_room, stage=stage, wedge=wedge, sector=sector, category=category)


def select_deck_lints(kb: KB, *, stage=None, wedge=None, sector=None) -> list[dict]:
    return _filter(kb.deck_lints, stage=stage, wedge=wedge, sector=sector)


def select_benchmarks(kb: KB, *, stage=None, wedge=None, sector=None) -> list[dict]:
    return _filter(kb.benchmarks, stage=stage, wedge=wedge, sector=sector)
