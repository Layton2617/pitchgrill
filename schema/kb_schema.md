# pitchgrill KB schema

KB 的最终产物是一个 JSON 文件,顶层结构:

```json
{
  "cells": [
    { "cell": "rf:team:seed", "type": "red_flag", "wedge": "general", "items": [ ... ] }
  ],
  "total_items": 480
}
```

每个 `cell` 是一组同类条目的集合(同一 type、同一 wedge)。`cell` 字段是人类可读的 id(用于落盘文件名);`type` 决定 items 里每条的字段;`wedge` 是该 cell 所属的赛道(`general` / `cross-border-cn` / `ai-dev-tools`)。

落盘后(见 `scripts/explode_kb.py`)每个 cell 变成一个 yaml 文件:

```
kb/red_flags/<cell>.yaml
kb/grilling/<cell>.yaml
kb/data_room/<cell>.yaml
kb/deck_lints/<cell>.yaml
kb/benchmarks/<cell>.yaml
```

yaml 文件内容就是该 cell 对象本身(`cell` / `type` / `wedge` / `items`)。

---

## 5 种 item

### red_flag — 红旗

投资人会一票否决或显著扣分的失分项,带可判定的阈值。

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | str | 全局唯一 id |
| `domain` | str | 领域,如 `team` / `market` / `unit_economics` / `cap_table` |
| `stage` | list[str] | 适用轮次,如 `["pre-seed", "seed"]` |
| `wedge` | str | 赛道 |
| `title` | str | 一句话红旗名 |
| `why` | str | 为什么是红旗(投资人视角) |
| `threshold` | str | 触发阈值,如 "单一客户营收占比 > 30%" |
| `severity` | str | `kill` / `major` / `minor` |
| `detect` | str | 怎么从 deck/自述里检出 |
| `sources` | list[str] | 出处 |

### grilling — 投资人拷问

会上最可能问倒人的尖锐问题,带强答 / 弱答示范。

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | str | 唯一 id |
| `theme` | str | 主题,如 `defensibility` / `gtm` / `retention` |
| `stage` | list[str] | 适用轮次 |
| `wedge` | str | 赛道 |
| `question` | str | 问题原文 |
| `strong_answer` | str | 一个好答案长什么样 |
| `weak_answer` | str | 一个会暴露问题的答案 |
| `sources` | list[str] | 出处 |

### data_room — data room 清单

DD 阶段投资人会要的材料。

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | str | 唯一 id |
| `category` | str | 分类,如 `legal` / `financial` / `product` |
| `stage` | list[str] | 适用轮次 |
| `wedge` | str | 赛道 |
| `document` | str | 材料名 |
| `required` | bool | 是否必备(false = 加分项) |
| `note` | str | 备注 / 常见坑 |

### deck_lint — deck 检查项

pitch deck 本身的常见问题。

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | str | 唯一 id |
| `stage` | list[str] | 适用轮次 |
| `wedge` | str | 赛道 |
| `issue` | str | 问题 |
| `why` | str | 为什么是问题 |
| `fix` | str | 怎么改 |

### benchmark — 行业基准

按 sector / metric 的健康区间与红线。

| 字段 | 类型 | 含义 |
|------|------|------|
| `sector` | str | 行业,如 `saas` / `marketplace` |
| `metric` | str | 指标,如 `gross_margin` / `net_revenue_retention` |
| `stage` | list[str] | 适用轮次 |
| `wedge` | str | 赛道 |
| `healthy` | str | 健康区间 |
| `red_flag` | str | 红线 |
| `note` | str | 备注 |
| `sources` | list[str] | 出处 |

---

## wedge 语义

- `general` 的条目对**所有** wedge 适用,查询时始终包含。
- 指定某个 wedge(`cross-border-cn` / `ai-dev-tools`)时,在 general 基础上**叠加**该 wedge 专属条目。
