"""对抗式融资就绪体检的核心。

输入 stage/sector/wedge/deck/自述 → 用 KB 选出相关条目 → 构造 grounded prompt
让模型扮演挑剔的投资人对照具体红旗审查这份 deck。有 ANTHROPIC_API_KEY 就调模型,
没有就降级为确定性输出(直接结构化列出匹配到的 KB 条目)。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from . import kb as kb_mod

MODEL = "claude-sonnet-4-6"  # 可配置
MAX_TOKENS = 8000

# 无 key 降级时每类最多展示多少条,避免把整个 KB 倒出来
DET_CAPS = {"red_flags": 15, "grilling": 10, "data_room": 24, "deck_lints": 8, "benchmarks": 12}
_SEV = {"kill": 0, "major": 1, "minor": 2}


@dataclass
class Selection:
    """从 KB 中按 stage/sector/wedge 选出的相关条目。"""

    red_flags: list[dict] = field(default_factory=list)
    grilling: list[dict] = field(default_factory=list)
    data_room: list[dict] = field(default_factory=list)
    deck_lints: list[dict] = field(default_factory=list)
    benchmarks: list[dict] = field(default_factory=list)


@dataclass
class Result:
    stage: str
    sector: str | None
    wedge: str
    selection: Selection
    analysis: str | None  # 模型产出的 deck 专属分析;降级时为 None
    grounded: bool        # True = 调了模型
    narrowed: bool = False  # True = 降级模式下按相关度+严重度收敛过的清单


def select(kb: kb_mod.KB, *, stage, sector, wedge) -> Selection:
    return Selection(
        red_flags=kb_mod.select_red_flags(kb, stage=stage, wedge=wedge),
        grilling=kb_mod.select_grilling(kb, stage=stage, wedge=wedge),
        data_room=kb_mod.select_data_room(kb, stage=stage, wedge=wedge),
        deck_lints=kb_mod.select_deck_lints(kb, stage=stage, wedge=wedge),
        benchmarks=kb_mod.select_benchmarks(kb, stage=stage, wedge=wedge, sector=sector),
    )


def _terms(text: str) -> set:
    return set(re.findall(r"[a-z]{4,}", (text or "").lower()))


def _overlap(item: dict, deck_terms: set) -> int:
    blob = " ".join(
        str(item.get(k, ""))
        for k in ("title", "threshold", "detect", "why", "question", "weak_answer",
                  "issue", "fix", "metric", "red_flag", "document", "note")
    )
    return len(_terms(blob) & deck_terms)


def _narrow(sel: Selection, deck: str, founder: str) -> Selection:
    """降级模式:按 (与 deck 的关键词相关度↓, severity↑) 收敛成可读清单。

    关键词匹配只是粗启发(deck 多为中文时命中弱),所以严重度做兜底排序,
    并由调用方在报告里标注'非 deck 专属诊断'。
    """
    dt = _terms(f"{deck}\n{founder}")
    rf = sorted(sel.red_flags, key=lambda f: (-_overlap(f, dt), _SEV.get(f.get("severity"), 9)))
    gr = sorted(sel.grilling, key=lambda g: -_overlap(g, dt))
    dr_req = [d for d in sel.data_room if d.get("required")]
    dr_opt = [d for d in sel.data_room if not d.get("required")]
    return Selection(
        red_flags=rf[: DET_CAPS["red_flags"]],
        grilling=gr[: DET_CAPS["grilling"]],
        data_room=(dr_req + dr_opt)[: DET_CAPS["data_room"]],
        deck_lints=sel.deck_lints[: DET_CAPS["deck_lints"]],
        benchmarks=sel.benchmarks[: DET_CAPS["benchmarks"]],
    )


SYSTEM = (
    "你是一位以挑剔著称的早期投资人,正在做投前尽调。下面给你一份创始人的 deck 文本和自述,"
    "以及一个结构化的领域知识库(红旗 + 阈值、分阶段拷问、data room 清单、benchmark)。"
    "你的任务不是给项目打分或预测成功率(早期项目 base rate 极低,预测无意义),"
    "而是只做失分项自检:严格对照知识库里的具体红旗和阈值,审查这份 deck。\n\n"
    "输出三段(用 markdown):\n"
    "1. 命中的红旗 —— 逐条说明 deck 里哪句话/哪个数据触发了知识库里的哪条红旗,"
    "引用阈值,标注 severity。没命中的不要编。\n"
    "2. 最可能问倒人的拷问 —— 从知识库拷问里挑出针对这份 deck 最致命的几条,"
    "并基于 deck 现状预判创始人会怎么弱答。\n"
    "3. Data room 缺口 —— 对照清单,指出这份 deck/自述里看不到、DD 时会被要的材料。\n\n"
    "只依据知识库和 deck 内容,不要引入知识库之外的判断标准。"
)


def _build_user_prompt(deck: str, founder: str, sel: Selection) -> str:
    kb_blob = json.dumps(
        {
            "red_flags": sel.red_flags,
            "grilling": sel.grilling,
            "data_room": sel.data_room,
            "deck_lints": sel.deck_lints,
            "benchmarks": sel.benchmarks,
        },
        ensure_ascii=False,
        indent=2,
    )
    return (
        f"## 知识库(你的审查依据)\n```json\n{kb_blob}\n```\n\n"
        f"## Deck 文本\n{deck or '(空)'}\n\n"
        f"## 创始人自述\n{founder or '(空)'}\n"
    )


def run(
    *,
    stage: str,
    sector: str | None,
    wedge: str,
    deck: str,
    founder: str,
    kb: kb_mod.KB | None = None,
    model: str = MODEL,
) -> Result:
    kb = kb if kb is not None else kb_mod.load_kb()
    sel = select(kb, stage=stage, sector=sector, wedge=wedge)

    analysis = None
    grounded = False
    if os.environ.get("ANTHROPIC_API_KEY") and not kb.is_empty:
        analysis = _call_model(deck, founder, sel, model)
        grounded = analysis is not None

    narrowed = False
    if not grounded and not kb.is_empty:
        sel = _narrow(sel, deck, founder)
        narrowed = True

    return Result(
        stage=stage,
        sector=sector,
        wedge=wedge,
        selection=sel,
        analysis=analysis,
        grounded=grounded,
        narrowed=narrowed,
    )


def _call_model(deck: str, founder: str, sel: Selection, model: str) -> str | None:
    try:
        import anthropic
    except ImportError:
        return None

    client = anthropic.Anthropic()
    with client.messages.stream(
        model=model,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        system=SYSTEM,
        messages=[{"role": "user", "content": _build_user_prompt(deck, founder, sel)}],
    ) as stream:
        msg = stream.get_final_message()

    return "".join(b.text for b in msg.content if b.type == "text")
