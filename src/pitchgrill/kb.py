"""加载 kb/ 下所有 yaml,建内存索引,提供按维度过滤的查询。

general wedge 的条目对所有 wedge 适用;指定 wedge 时叠加该 wedge 专属条目。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KB_ROOT = REPO_ROOT / "kb"

GENERAL = "general"

# type -> 落盘子目录
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
                # benchmark 的 item 没有 wedge 字段时,从 cell 继承
                item.setdefault("wedge", wedge)
                bucket.append(item)
    return kb


def _stage_match(item: dict, stage: str | None) -> bool:
    if stage is None:
        return True
    stages = item.get("stage")
    if not stages:  # 没标 stage 视为通用
        return True
    return stage in stages


def _wedge_match(item: dict, wedge: str | None) -> bool:
    iw = item.get("wedge", GENERAL)
    if iw == GENERAL:
        return True
    if wedge is None:
        return False
    return iw == wedge


def _filter(items: list[dict], *, stage=None, wedge=None, **exact) -> list[dict]:
    out = []
    for it in items:
        if not _stage_match(it, stage):
            continue
        if not _wedge_match(it, wedge):
            continue
        if any(it.get(k) != v for k, v in exact.items() if v is not None):
            continue
        out.append(it)
    return out


def select_red_flags(kb: KB, *, stage=None, wedge=None, domain=None) -> list[dict]:
    return _filter(kb.red_flags, stage=stage, wedge=wedge, domain=domain)


def select_grilling(kb: KB, *, stage=None, wedge=None, theme=None) -> list[dict]:
    return _filter(kb.grilling, stage=stage, wedge=wedge, theme=theme)


def select_data_room(kb: KB, *, stage=None, wedge=None, category=None) -> list[dict]:
    return _filter(kb.data_room, stage=stage, wedge=wedge, category=category)


def select_deck_lints(kb: KB, *, stage=None, wedge=None) -> list[dict]:
    return _filter(kb.deck_lints, stage=stage, wedge=wedge)


def select_benchmarks(kb: KB, *, stage=None, wedge=None, sector=None) -> list[dict]:
    return _filter(kb.benchmarks, stage=stage, wedge=wedge, sector=sector)
