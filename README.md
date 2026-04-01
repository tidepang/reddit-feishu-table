# Feishu Team Intel V1

`v1` 目标是先把电子音乐相关的公开情报稳定写进飞书多维表，不一开始就啃小红书和 Instagram 的复杂采集。

如果你想把这套东西发成 GitHub starter repo，先看：

- `docs/BASE_SCHEMA.md`
- `docs/PUBLISHING.md`

当前结构分两层：

- `scripts/collect_intel_v1.py`
  - 直接抓网页 RSS 源
  - 做关键词过滤、简单评分、去重
  - 通过 `lark-cli` 写入飞书 Base
- `scripts/ingest_reddit_export.py`
  - 把后续拿到的 Reddit 导出 JSON 写进同一张表
  - 先不把 Reddit 的在线采集做成 blocker
- `scripts/generate_weekly_topic_packet.py`
  - 从 `自动情报采集` 视图读取最近 7 天记录
  - 生成周报 Markdown、JSON 数据包、可直接喂给 LLM 的 Prompt
- `scripts/publish_weekly_report_to_base.py`
  - 把生成好的周报 Markdown 写回同一张飞书表
  - 默认新增一条 `记录类型=周报` 的记录
- `scripts/write_topics_from_editorial_report.py`
  - 从中文选题会周报里解析“适合小红书的 10 个选题”
  - 去重后写进同一张表，并落到 `自动情报采集` 视图

## 当前接入范围

已做成可直接跑的 `Web` 源：

- `DJ Mag` `https://djmag.com/rss.xml`
- `CDM` `https://cdm.link/feed/`
- `EDMTunes` `https://www.edmtunes.com/feed/`
- `We Rave You` `https://weraveyou.com/feed/`

飞书写入目标：

- Base: `Content Calendar`
- Table: `Table`
- View: `自动情报采集`

## 前置条件

1. 本机已安装并授权 `lark-cli`
2. `lark-cli auth status` 显示当前是 `user`
3. 本地配置文件存在：

```bash
config/intel_v1.local.json
```

如果你是第一次使用这套仓库，建议先复制示例配置：

```bash
cp config/intel_v1.example.json config/intel_v1.local.json
```

## 快速开始

如果你喜欢 `make` 入口：

```bash
make dry-run
make pipeline
```

先看会写入什么：

```bash
python3 scripts/collect_intel_v1.py --config config/intel_v1.local.json --dry-run
```

确认没问题后正式写入：

```bash
python3 scripts/collect_intel_v1.py --config config/intel_v1.local.json --write
```

限制每个源只抓 5 条：

```bash
python3 scripts/collect_intel_v1.py --config config/intel_v1.local.json --write --limit-per-source 5
```

一条命令跑完“采集 + 生成周报包”：

```bash
bash scripts/run_intel_pipeline.sh
```

如果只想临时控制采集量：

```bash
LIMIT_PER_SOURCE=5 bash scripts/run_intel_pipeline.sh
```

这条命令现在还会自动把当天周报写回飞书 Base。

## Reddit 接入

当前环境下，Reddit 的公开端点容易直接返回 `403`，所以 `v1` 不把它做成在线强依赖。

现在的做法是：

1. 你先用后续选定的 Reddit 导出方式拿到 JSON
2. 用下面的命令写进同一张飞书表

```bash
python3 scripts/ingest_reddit_export.py \
  --config config/intel_v1.local.json \
  --input /path/to/reddit-export.json \
  --write
```

## 生成每周选题包

从飞书里的 `自动情报采集` 视图生成本周数据包：

```bash
python3 scripts/generate_weekly_topic_packet.py --config config/intel_v1.local.json
```

输出文件默认写到 `data/`：

- `weekly_packet_YYYYMMDD.json`
- `weekly_report_YYYYMMDD.md`
- `weekly_prompt_YYYYMMDD.md`

如果存在 `weekly_editorial_report_*.md` 版本，流水线会优先把它写回飞书；否则回写默认 `weekly_report_*.md`。

## 把周报选题写回自动情报

如果已经有一份中文选题会周报，可以直接把其中的选题写进 `自动情报采集` 视图：

```bash
python3 scripts/write_topics_from_editorial_report.py \
  --config config/intel_v1.local.json \
  --report-file data/weekly_editorial_report_20260401.md
```

这些写回记录会使用：

- `记录类型` = `自动情报`
- `来源平台` = `选题`
- `来源账号/网站` = `周报选题生成`
- `是否转选题` = `已选中`

同时不会参与下一轮 `weekly_packet` 统计，因为它们默认不写 `来源链接`。

如果只想改统计窗口：

```bash
python3 scripts/generate_weekly_topic_packet.py \
  --config config/intel_v1.local.json \
  --days 7 \
  --top-n 12
```

支持的输入字段尽量宽松，只要能提供这些字段里的大部分就行：

- `title`
- `url`
- `subreddit`
- `author`
- `created_utc` 或 `created_at`
- `score`
- `num_comments`
- `selftext`

## 字段映射

采集脚本会写这些字段：

- `记录类型` = `自动情报`
- `标题`
- `来源平台`
- `来源链接`
- `来源账号/网站`
- `采集时间`
- `情报关键词`
- `情报摘要`
- `情报评分`
- `是否转选题` = `待判断`

## 简单规则

### 去重

- 优先按 `来源链接`
- 其次按标准化后的 `标题`

### 评分

网页 RSS 使用简单规则：

- 相关性：关键词命中越多越高
- 新鲜度：越近越高
- 可转译度：包含榜单、趋势、教程、艺人、festival、release 等词更高

Reddit 导入额外会把 `score` 和 `num_comments` 算进去。

## 后续建议

跑顺后再补：

1. Reddit 在线采集
2. Instagram 账号/hashtag 采集
3. 小红书只读采集
4. 每周自动汇总成选题周报

## 开源分享建议

最适合把这个仓库定位成：

- 一个 starter repo
- 一个 “Feishu Base + RSS + Weekly Topic Packet” 的最小实现

而不是：

- 你团队内部生产环境的完整镜像
- 带真实 Base token / 数据 / 周报样本的工作仓库
