"""Format an engine.Result into a three-section Markdown report."""
from __future__ import annotations

from .engine import Result, Selection

_SEVERITY_ORDER = {"kill": 0, "major": 1, "minor": 2}
_SEVERITY_LABEL = {"kill": "🔴 KILL", "major": "🟠 MAJOR", "minor": "🟡 MINOR"}


def _sources(item: dict) -> str:
    srcs = item.get("sources") or []
    return f" _({'; '.join(srcs)})_" if srcs else ""


def _red_flags_section(sel: Selection) -> str:
    flags = sorted(
        sel.red_flags,
        key=lambda f: _SEVERITY_ORDER.get(f.get("severity"), 9),
    )
    lines = ["## 1. Red flags\n"]
    if not flags:
        lines.append("_No matching red flags for this stage/wedge._\n")
        return "\n".join(lines)
    for f in flags:
        sev = _SEVERITY_LABEL.get(f.get("severity"), f.get("severity", "?"))
        lines.append(f"### {sev} — {f.get('title', f.get('id', '?'))}")
        if f.get("domain"):
            lines.append(f"- **domain**: {f['domain']}")
        if f.get("threshold"):
            lines.append(f"- **threshold**: {f['threshold']}")
        if f.get("why"):
            lines.append(f"- **why**: {f['why']}")
        if f.get("detect"):
            lines.append(f"- **how to spot**: {f['detect']}")
        lines.append(f"- source: {_sources(f).strip() or '—'}")
        lines.append("")
    return "\n".join(lines)


def _grilling_section(sel: Selection) -> str:
    lines = ["## 2. You will be asked\n"]
    if not sel.grilling:
        lines.append("_No matching questions for this stage/wedge._\n")
        return "\n".join(lines)
    for g in sel.grilling:
        lines.append(f"### Q ({g.get('theme', '?')}): {g.get('question', '?')}")
        if g.get("strong_answer"):
            lines.append(f"- ✅ **strong answer**: {g['strong_answer']}")
        if g.get("weak_answer"):
            lines.append(f"- ❌ **weak answer (gives you away)**: {g['weak_answer']}")
        lines.append(f"- source: {_sources(g).strip() or '—'}")
        lines.append("")
    return "\n".join(lines)


def _data_room_section(sel: Selection) -> str:
    lines = ["## 3. Data-room gaps\n"]
    if not sel.data_room:
        lines.append("_No matching data-room items for this stage/wedge._\n")
        return "\n".join(lines)
    required = [d for d in sel.data_room if d.get("required")]
    optional = [d for d in sel.data_room if not d.get("required")]

    def _block(title, docs):
        if not docs:
            return []
        out = [f"### {title}"]
        for d in docs:
            note = f" — {d['note']}" if d.get("note") else ""
            cat = f"[{d['category']}] " if d.get("category") else ""
            out.append(f"- {cat}{d.get('document', '?')}{note}")
        out.append("")
        return out

    lines += _block("Must have", required)
    lines += _block("Nice to have", optional)
    return "\n".join(lines)


def render(result: Result) -> str:
    head = [
        "# Fundraising readiness report",
        "",
        f"- stage: `{result.stage}` | sector: `{result.sector or '—'}` | wedge: `{result.wedge}`",
        f"- matched: {len(result.selection.red_flags)} red flags / "
        f"{len(result.selection.grilling)} questions / "
        f"{len(result.selection.data_room)} data-room items / "
        f"{len(result.selection.deck_lints)} deck lints / "
        f"{len(result.selection.benchmarks)} benchmarks",
        "",
        "> Not a score. This does not predict your odds of success "
        "(early-stage base rates are too low) — it surfaces the losing moves.",
        "",
    ]

    parts = ["\n".join(head)]

    if result.grounded and result.analysis:
        parts.append("## 0. Analysis of your deck\n\n" + result.analysis + "\n")
    elif result.selection and result.selection.red_flags == [] and _all_empty(result.selection):
        parts.append(
            "## 0. Note\n\n"
            "_The knowledge base is empty, or nothing matches this stage/wedge. "
            "Build it first: `python scripts/explode_kb.py <kb.json>`._\n"
        )
    else:
        parts.append(
            "## 0. Note\n\n"
            "_No `ANTHROPIC_API_KEY` found, so this is **checklist mode**: the most relevant "
            "items for this stage/sector/wedge, ranked by keyword overlap with your deck and "
            "severity — not a per-deck diagnosis. Set `ANTHROPIC_API_KEY` to get a line-by-line "
            "read of which sentence in your deck triggers which red flag._\n"
        )

    parts.append(_red_flags_section(result.selection))
    parts.append(_grilling_section(result.selection))
    parts.append(_data_room_section(result.selection))

    return "\n".join(parts)


def _all_empty(sel: Selection) -> bool:
    return not any(
        (sel.red_flags, sel.grilling, sel.data_room, sel.deck_lints, sel.benchmarks)
    )
