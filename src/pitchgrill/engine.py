"""The engine.

Inputs (stage/sector/wedge/deck/founder note) -> pick relevant KB items -> build a
grounded prompt that has the model play a skeptical investor checking the deck against
specific red flags. With ANTHROPIC_API_KEY it calls the model; without it, it falls back
to checklist mode (the matched KB items, ranked).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from . import kb as kb_mod

MODEL = "claude-sonnet-4-6"  # configurable
MAX_TOKENS = 8000

# Checklist-mode caps per category, so we don't dump the whole KB without a key
DET_CAPS = {"red_flags": 15, "grilling": 10, "data_room": 24, "deck_lints": 8, "benchmarks": 12}
_SEV = {"kill": 0, "major": 1, "minor": 2}


@dataclass
class Selection:
    """KB items selected by stage/sector/wedge."""

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
    analysis: str | None  # per-deck analysis from the model; None in checklist mode
    grounded: bool        # True = the model was called
    narrowed: bool = False  # True = checklist mode ranked by relevance + severity


def select(kb: kb_mod.KB, *, stage, sector, wedge) -> Selection:
    return Selection(
        red_flags=kb_mod.select_red_flags(kb, stage=stage, wedge=wedge, sector=sector),
        grilling=kb_mod.select_grilling(kb, stage=stage, wedge=wedge, sector=sector),
        data_room=kb_mod.select_data_room(kb, stage=stage, wedge=wedge, sector=sector),
        deck_lints=kb_mod.select_deck_lints(kb, stage=stage, wedge=wedge, sector=sector),
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
    """Checklist mode: rank by (keyword overlap with the deck desc, severity asc) and cap.

    Keyword overlap is a rough heuristic (weak when the deck isn't in English), so severity
    is the tie-breaker, and the caller labels the report as 'not a per-deck diagnosis'.
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
    "You are a notoriously skeptical early-stage investor doing pre-investment diligence. "
    "Below is a founder's pitch deck and note, plus a structured knowledge base (red flags "
    "with thresholds, stage-specific grilling questions, a data-room checklist, benchmarks). "
    "Your job is NOT to score the company or predict its odds of success (early-stage base "
    "rates are too low for that to mean anything). It is to surface the losing moves: check "
    "this deck strictly against the specific red flags and thresholds in the knowledge base.\n\n"
    "Output three sections (markdown):\n"
    "1. Red flags hit — for each, name the exact line or number in the deck that triggers which "
    "red flag, cite the threshold, and mark the severity. Do not invent hits that aren't there.\n"
    "2. You will be asked — pick the questions from the knowledge base that are most lethal for "
    "this specific deck, and predict the weak answer the founder is likely to give.\n"
    "3. Data-room gaps — against the checklist, name the documents this deck/note doesn't show "
    "that diligence will demand.\n\n"
    "Use only the knowledge base and the deck. Do not introduce judgment criteria from outside it."
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
        f"## Knowledge base (your checklist)\n```json\n{kb_blob}\n```\n\n"
        f"## Deck\n{deck or '(empty)'}\n\n"
        f"## Founder note\n{founder or '(empty)'}\n"
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
