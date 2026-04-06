# OpenClaw Integration

This repository can be driven from OpenClaw on the same machine.

The simplest setup is:

- keep `lark-cli` authorized locally
- keep this repo on the same Mac
- let OpenClaw call the wrapper script in `scripts/openclaw_intel.sh`

That keeps the responsibilities clear:

- this repo handles collection, deduplication, Base writes, weekly packets, and topic write-back
- OpenClaw handles natural-language triggering, follow-up analysis, and chat-first interaction

## Recommended Same-Machine Setup

OpenClaw does not need a separate Feishu token system if it runs on the same computer and can reuse the already-authorized `lark-cli` environment.

Use these commands directly:

```bash
bash scripts/openclaw_intel.sh status
bash scripts/openclaw_intel.sh collect
bash scripts/openclaw_intel.sh weekly
bash scripts/openclaw_intel.sh publish
bash scripts/openclaw_intel.sh pipeline
```

If you want a shorter natural-language entry point, use:

```bash
bash scripts/ask_openclaw_intel.sh "跑一下今天的 pipeline，然后用 4 条 bullet 告诉我结果"
```

That wrapper still uses the same local OpenClaw skill and the same-machine `lark-cli` auth. It just hides the long `openclaw agent --local ...` command.

Optional env vars:

```bash
OPENCLAW_INTEL_CONFIG=/absolute/path/to/config/intel_v1.local.json
LIMIT_PER_SOURCE=5
WINDOW_DAYS=7
TOP_N=12
```

## OpenClaw Prompt Examples

Examples for direct local agent use:

```bash
openclaw agent --local --message "Use $feishu-team-intel to check the local Feishu intelligence workflow status on this Mac."
```

```bash
openclaw agent --local --message "Use $feishu-team-intel to run the full local pipeline for the Feishu intelligence repo, then summarize what changed."
```

```bash
openclaw agent --local --message "Use $feishu-team-intel to inspect the latest weekly packet and tell me the three strongest topic directions."
```

Chinese examples through the short wrapper:

```bash
bash scripts/ask_openclaw_intel.sh "看下当前 workflow 状态"
bash scripts/ask_openclaw_intel.sh "跑一下今天的 pipeline，然后告诉我有没有新信号、周报有没有写回飞书"
bash scripts/ask_openclaw_intel.sh "分析最新周报，给我 5 个更值得写的话题"
```

## Why This Split Works

This is the recommended split:

- system scheduler or manual shell command: when something should run
- this repo: what the pipeline does
- OpenClaw: how a human asks for it, inspects it, or extends it

OpenClaw is best used as the language layer and orchestration layer, not as the lowest-level collector.
