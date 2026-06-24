# pitchgrill KB schema

The KB is built from a single JSON file shaped like:

```json
{
  "cells": [
    { "cell": "rf:team:seed", "type": "red_flag", "wedge": "general", "items": [ ... ] }
  ],
  "total_items": 480
}
```

A `cell` is a group of same-kind items (same `type`, same `wedge`). `cell` is a human-readable id (used as the on-disk filename); `type` decides the fields on each item in `items`; `wedge` is the niche the cell belongs to (`general` / `cross-border-cn` / `ai-dev-tools`).

After exploding (see `scripts/explode_kb.py`) each cell becomes one yaml file:

```
kb/red_flags/<cell>.yaml
kb/grilling/<cell>.yaml
kb/data_room/<cell>.yaml
kb/deck_lints/<cell>.yaml
kb/benchmarks/<cell>.yaml
```

The yaml content is the cell object itself (`cell` / `type` / `wedge` / `items`).

---

## The five item types

### red_flag

A losing move an investor will pass on or dock heavily, with a checkable threshold.

| field | type | meaning |
|------|------|------|
| `id` | str | globally unique id |
| `domain` | str | e.g. `team` / `market` / `unit_economics` / `cap_table` |
| `stage` | list[str] | applicable rounds, e.g. `["pre-seed", "seed"]` |
| `wedge` | str | niche |
| `title` | str | one-line name of the red flag |
| `why` | str | why it's a red flag (investor's view) |
| `threshold` | str | the trigger, e.g. "single customer > 30% of revenue" |
| `severity` | str | `kill` / `major` / `minor` |
| `detect` | str | how to spot it from the deck/note |
| `sources` | list[str] | sources |

### grilling

The sharp questions most likely to catch a founder out, with strong/weak answers.

| field | type | meaning |
|------|------|------|
| `id` | str | unique id |
| `theme` | str | e.g. `defensibility` / `gtm` / `retention` |
| `stage` | list[str] | applicable rounds |
| `wedge` | str | niche |
| `question` | str | the question, verbatim |
| `strong_answer` | str | what a good answer looks like |
| `weak_answer` | str | the answer that gives you away |
| `sources` | list[str] | sources |

### data_room

Documents diligence will ask for.

| field | type | meaning |
|------|------|------|
| `id` | str | unique id |
| `category` | str | e.g. `legal` / `financial` / `product` |
| `stage` | list[str] | applicable rounds |
| `wedge` | str | niche |
| `document` | str | the document |
| `required` | bool | must-have (false = nice-to-have) |
| `note` | str | note / common pitfall |

### deck_lint

Problems with the pitch deck itself.

| field | type | meaning |
|------|------|------|
| `id` | str | unique id |
| `stage` | list[str] | applicable rounds |
| `wedge` | str | niche |
| `issue` | str | the problem |
| `why` | str | why it's a problem |
| `fix` | str | how to fix it |

### benchmark

Healthy ranges and red lines per sector and metric.

| field | type | meaning |
|------|------|------|
| `sector` | str | e.g. `saas` / `marketplace` |
| `metric` | str | e.g. `gross_margin` / `net_revenue_retention` |
| `stage` | list[str] | applicable rounds |
| `wedge` | str | niche |
| `healthy` | str | healthy range |
| `red_flag` | str | the red line |
| `note` | str | note |
| `sources` | list[str] | sources |

---

## Wedge semantics

- `general` items apply to **every** wedge and are always included.
- Passing a wedge (`cross-border-cn` / `ai-dev-tools`) **stacks** that wedge's items on top of `general`.
