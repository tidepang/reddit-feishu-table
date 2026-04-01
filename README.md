# Feishu Team Intel V1

A starter repo for turning public signals into a Feishu-native topic workflow.

This project collects public web signals, writes them into Feishu Base through `lark-cli`, generates a weekly topic packet, and writes selected topic candidates back into the same workflow. It is designed for small content teams that already use Feishu and want a lightweight intelligence pipeline instead of a separate database and dashboard stack.

`v1` intentionally starts with stable public sources such as RSS and exported community data. The goal is to prove the workflow first, then expand to more fragile channels later.

## What This Repo Does

This repo handles four jobs:

1. Collects public signals from configured sources
2. Filters, deduplicates, and scores them
3. Writes structured records into Feishu Base
4. Generates weekly reports and topic candidates from those records

It is not a universal crawler. It is a starter workflow for content intelligence.

## Who This Is For

This repo is a good fit for:

- content teams using Feishu as their main collaboration tool
- strategy or editorial teams that need a lightweight topic radar
- solo creators who want signals, reports, and topic candidates in one place
- teams that want to start with public sources before adding more complex collectors

## Workflow

The default workflow is:

`public sources -> Feishu Base -> weekly packet -> editorial report -> candidate topics`

Current scripts map to that flow:

- `scripts/collect_intel_v1.py`
  - collects RSS-based signals
  - applies keyword matching, scoring, and deduplication
  - writes records into Feishu Base through `lark-cli`
- `scripts/ingest_reddit_export.py`
  - imports exported Reddit JSON into the same Base
  - keeps Reddit as an optional input, not a hard runtime dependency
- `scripts/generate_weekly_topic_packet.py`
  - reads recent records from the `自动情报采集` view
  - generates Markdown, JSON, and a prompt-ready packet
- `scripts/publish_weekly_report_to_base.py`
  - writes a generated weekly report back into the same Base
- `scripts/write_topics_from_editorial_report.py`
  - extracts topic candidates from a Chinese editorial report
  - writes them back into the `自动情报采集` view as structured records

## Default Inputs

The example config ships with a few general-purpose web sources:

- `Hacker News` `https://hnrss.org/frontpage`
- `TechCrunch` `https://techcrunch.com/feed/`
- `The Verge` `https://www.theverge.com/rss/index.xml`
- `OpenAI News` `https://openai.com/news/rss.xml`

These are placeholders, not opinions. Replace both the keywords and the sources with feeds that match the domain you actually care about.

## Feishu Target

The repo expects one Feishu Base table as the central store.

Default examples in this repo assume:

- Base: `Content Calendar`
- Table: `Table`
- View: `自动情报采集`

Schema details live in [docs/BASE_SCHEMA.md](/Users/tidepang/2026project/feishu-team/docs/BASE_SCHEMA.md).

Publishing guidance for making this repo reusable lives in [docs/PUBLISHING.md](/Users/tidepang/2026project/feishu-team/docs/PUBLISHING.md).

## Prerequisites

Before running the pipeline:

1. Install and authorize `lark-cli`
2. Make sure `lark-cli auth status` shows a valid `user` identity
3. Prepare a local config file

Create the local config from the example:

```bash
cp config/intel_v1.example.json config/intel_v1.local.json
```

Then update:

- `base.base_token`
- `base.table_id`
- `base.view_id`
- `keywords`
- `sources`

## Quick Start

Preview what would be written:

```bash
python3 scripts/collect_intel_v1.py --config config/intel_v1.local.json --dry-run
```

Write records into Feishu Base:

```bash
python3 scripts/collect_intel_v1.py --config config/intel_v1.local.json --write
```

Limit how many entries are fetched from each source:

```bash
python3 scripts/collect_intel_v1.py --config config/intel_v1.local.json --write --limit-per-source 5
```

Run the end-to-end pipeline:

```bash
bash scripts/run_intel_pipeline.sh
```

If `make` is preferred:

```bash
make dry-run
make pipeline
```

## Weekly Packet Output

Generate the weekly packet from the records already stored in Feishu Base:

```bash
python3 scripts/generate_weekly_topic_packet.py --config config/intel_v1.local.json
```

The script writes these files into `data/`:

- `weekly_packet_YYYYMMDD.json`
- `weekly_report_YYYYMMDD.md`
- `weekly_prompt_YYYYMMDD.md`

The report can then be published back into Feishu Base:

```bash
python3 scripts/publish_weekly_report_to_base.py \
  --config config/intel_v1.local.json \
  --report-file data/weekly_report_YYYYMMDD.md \
  --packet-file data/weekly_packet_YYYYMMDD.json
```

## Writing Topic Candidates Back Into Base

If an editorial report already exists, its topic section can be written back into the same Base:

```bash
python3 scripts/write_topics_from_editorial_report.py \
  --config config/intel_v1.local.json \
  --report-file data/weekly_editorial_report_20260401.md
```

These records are written as:

- `记录类型 = 自动情报`
- `来源平台 = 选题`
- `来源账号/网站 = 周报选题生成`
- `是否转选题 = 已选中`

They are intentionally written without `来源链接`, so they do not re-enter the next weekly packet as source signals.

## Reddit Import

`v1` keeps Reddit simple. Instead of depending on live scraping, it imports exported JSON:

```bash
python3 scripts/ingest_reddit_export.py \
  --config config/intel_v1.local.json \
  --input /path/to/reddit-export.json \
  --write
```

Expected fields are flexible, but these are the most useful:

- `title`
- `url`
- `subreddit`
- `author`
- `created_utc` or `created_at`
- `score`
- `num_comments`
- `selftext`

## Record Shape

The collection scripts write these fields:

- `记录类型 = 自动情报`
- `标题`
- `来源平台`
- `来源链接`
- `来源账号/网站`
- `采集时间`
- `情报关键词`
- `情报摘要`
- `情报评分`
- `是否转选题 = 待判断`

## Built-In Heuristics

Deduplication:

- first by `来源链接`
- then by normalized `标题`

Web scoring:

- relevance: more configured keyword hits score higher
- freshness: newer items score higher
- usefulness: list-style, tutorial, case, analysis, workflow, and review language scores higher

Reddit import also incorporates:

- `score`
- `num_comments`

## Extension Path

After the basic loop is working, the most natural next steps are:

1. live Reddit collection
2. more communities or social inputs
3. domain-specific source packs
4. stronger weekly summarization and downstream editorial workflows

## Repository Positioning

This repository is best understood as:

- a starter repo
- a minimal `Feishu Base + RSS + Weekly Topic Packet` implementation
- a configurable content-intelligence workflow that can be repurposed by changing sources and keywords

It is not intended to be:

- a full internal production mirror of any one team
- a repo containing real Base tokens or private datasets
- a universal crawler for every platform
