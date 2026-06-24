"""把 engine.Result 格式化成三段 Markdown 报告。"""
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
    lines = ["## 1. 红旗扫描\n"]
    if not flags:
        lines.append("_当前 stage/wedge 下知识库没有匹配的红旗条目。_\n")
        return "\n".join(lines)
    for f in flags:
        sev = _SEVERITY_LABEL.get(f.get("severity"), f.get("severity", "?"))
        lines.append(f"### {sev} — {f.get('title', f.get('id', '?'))}")
        if f.get("domain"):
            lines.append(f"- **领域**:{f['domain']}")
        if f.get("threshold"):
            lines.append(f"- **阈值**:{f['threshold']}")
        if f.get("why"):
            lines.append(f"- **为什么**:{f['why']}")
        if f.get("detect"):
            lines.append(f"- **怎么检出**:{f['detect']}")
        lines.append(f"- 来源:{_sources(f).strip() or '—'}")
        lines.append("")
    return "\n".join(lines)


def _grilling_section(sel: Selection) -> str:
    lines = ["## 2. 对抗式拷问\n"]
    if not sel.grilling:
        lines.append("_当前 stage/wedge 下知识库没有匹配的拷问条目。_\n")
        return "\n".join(lines)
    for g in sel.grilling:
        lines.append(f"### Q（{g.get('theme', '?')}）：{g.get('question', '?')}")
        if g.get("strong_answer"):
            lines.append(f"- ✅ **强答**:{g['strong_answer']}")
        if g.get("weak_answer"):
            lines.append(f"- ❌ **弱答(会暴露问题)**:{g['weak_answer']}")
        lines.append(f"- 来源:{_sources(g).strip() or '—'}")
        lines.append("")
    return "\n".join(lines)


def _data_room_section(sel: Selection) -> str:
    lines = ["## 3. Data room 缺口清单\n"]
    if not sel.data_room:
        lines.append("_当前 stage/wedge 下知识库没有匹配的 data room 条目。_\n")
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

    lines += _block("必备", required)
    lines += _block("加分项", optional)
    return "\n".join(lines)


def render(result: Result) -> str:
    head = [
        "# 融资就绪体检报告",
        "",
        f"- stage: `{result.stage}` | sector: `{result.sector or '—'}` | wedge: `{result.wedge}`",
        f"- 匹配条目:红旗 {len(result.selection.red_flags)} / "
        f"拷问 {len(result.selection.grilling)} / "
        f"data room {len(result.selection.data_room)} / "
        f"deck lint {len(result.selection.deck_lints)} / "
        f"benchmark {len(result.selection.benchmarks)}",
        "",
        "> 本工具不预测成功概率(早期 base rate 极低),只做失分项自检。",
        "",
    ]

    parts = ["\n".join(head)]

    if result.grounded and result.analysis:
        parts.append("## 0. 针对你这份 deck 的对抗式分析\n\n" + result.analysis + "\n")
    elif result.selection and result.selection.red_flags == [] and _all_empty(result.selection):
        parts.append(
            "## 0. 提示\n\n"
            "_KB 尚未生成或当前 stage/wedge 无匹配条目。请先用 "
            "`python scripts/explode_kb.py <kb.json>` 落盘知识库。_\n"
        )
    else:
        parts.append(
            "## 0. 说明\n\n"
            "_未检测到 `ANTHROPIC_API_KEY`,降级为**清单模式**:按与 deck 的关键词相关度 + "
            "严重度收敛出当前 stage/sector/wedge 下最该自查的条目(非针对这份 deck 的命中诊断)。"
            "设置 `ANTHROPIC_API_KEY` 后会改为逐条指出 deck 里哪句话触发了哪条红旗。_\n"
        )

    parts.append(_red_flags_section(result.selection))
    parts.append(_grilling_section(result.selection))
    parts.append(_data_room_section(result.selection))

    return "\n".join(parts)


def _all_empty(sel: Selection) -> bool:
    return not any(
        (sel.red_flags, sel.grilling, sel.data_room, sel.deck_lints, sel.benchmarks)
    )
