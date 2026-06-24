# pitchgrill

Get grilled before the VCs do.

pitchgrill reads your pitch deck and tells you where a skeptical investor will dock you points: the red flags that kill deals in diligence, the questions that will catch you flat-footed in the room, and the data-room documents you don't have yet.

It is not a scorer. It does not predict your odds of success (early-stage base rates are too low for that number to mean anything). It does one useful thing: surface the losing moves before an investor does.

> 中文说明见文末。

## Why not just ask ChatGPT

Paste your deck into a chatbot and you get polite, generic encouragement. pitchgrill ships a **structured knowledge base** that pins down what investors actually look for, as checkable rules:

- **Red flags with thresholds** — not "customer concentration looks a bit high" but "single customer > 30% of revenue = major flag, > 50% = deal-killer."
- **Stage-specific grilling** — the questions a pre-seed founder gets are not the ones a Series A founder gets. Each comes with what a strong answer sounds like and the weak answer that gives you away.
- **Data-room checklist** — the documents diligence will ask for, split into must-have vs. nice-to-have.
- **Deck lint** — the narrative mistakes that get a deck rejected on sight.
- **Sector benchmarks** — healthy ranges and red lines per sector and metric.

Everything lives in plain YAML under [`kb/`](kb/). You can read every threshold and its source, and edit any of it to match your own view.

## Quickstart

```bash
pip install -r requirements.txt

# Plain text or PDF deck. --founder is an optional free-text note.
python check.py \
  --deck examples/sample_deck.md \
  --stage seed \
  --sector dev-tools \
  --wedge ai-dev-tools
```

Set `ANTHROPIC_API_KEY` and pitchgrill reads your specific deck and tells you which line triggers which red flag. Without a key it falls back to a checklist mode: the most relevant items for your stage and sector, ranked, with no per-deck analysis.

## Example

For a seed-stage AI dev-tools deck where one customer is 81% of revenue and gross margin is 38%:

```
## Red flags

🔴 KILL  Revenue concentration in a single customer
  threshold: single customer > 50% of revenue
  evidence:  MegaCorp is $340K of $420K ARR (81%)

🔴 KILL  Gross margin far below sector norm
  threshold: SaaS healthy 70-80%+; services-heavy delivery is a flag
  evidence:  38% margin, plus 2 dedicated delivery engineers

## You will be asked

- "If MegaCorp churns tomorrow, are you still a seed company?"
- "38% margin with dedicated engineers — is this software or consulting?"
- "Walk me through the $50B TAM. Bottom-up, what can you actually reach?"

## Data-room gaps

- Revenue by customer / cohort
- Fully-diluted cap table (including the verbal advisor grant)
- Unit economics: CAC / LTV / payback / fully-loaded margin
```

## Wedges

Three knowledge layers. `general` always applies; pass `--wedge` to stack a niche layer on top:

- `general` — applies to everyone.
- `cross-border-cn` — Chinese / cross-border teams raising USD (VIE structure, ODI, US-VC objections to a China-based team).
- `ai-dev-tools` — AI and developer-tools startups (token-cost margins, "why won't the model provider just build this", data-moat questions).

## How it works

```
check.py                 entry point
src/pitchgrill/
  cli.py                 arg parsing, reads the deck (txt/pdf)
  kb.py                  loads kb/ yaml, filters by stage / sector / wedge
  engine.py              picks relevant items, builds a grounded prompt, calls the model (or falls back)
  report.py              renders the three sections
kb/                      the knowledge base (yaml)
scripts/                 maintenance: rebuild and source-check the kb
schema/kb_schema.md      the kb data shape
examples/                sample deck
```

The model only maps your deck onto the knowledge base. It does not invent judgment criteria beyond what's in `kb/`, which is why the output is auditable: every red flag points back to a rule and a source you can read.

## Customize

The knowledge base is the product. Edit the YAML in `kb/` to change a threshold, add a red flag, or tune the grilling for your own thesis. Contributions of new sectors and wedges are welcome.

To rebuild `kb/` from a single JSON file, or to re-check that every cited source URL is still live:

```bash
python scripts/explode_kb.py kb.json              # JSON -> kb/*.yaml
python scripts/check_sources.py kb.json --strip   # drop dead source links
```

## License

MIT. See [LICENSE](LICENSE).

---

## 中文

**pitchgrill** 吃你的 pitch deck,告诉你一个挑剔的投资人会在哪里扣分:DD 时会让流程死掉的红旗、会在会议室里问倒你的问题、你还缺的 data room 材料。

不是打分器,不预测成功率,只做失分项自检。区别于裸用 ChatGPT 的泛泛反馈,pitchgrill 带一个 [`kb/`](kb/) 下可读可改的结构化知识库:带阈值的红旗、分阶段拷问、data room 清单、deck lint、赛道 benchmark。设了 `ANTHROPIC_API_KEY` 就针对你的 deck 逐条命中,没设则降级为清单模式。三个 wedge:`general` / `cross-border-cn`(中国出海)/ `ai-dev-tools`。
