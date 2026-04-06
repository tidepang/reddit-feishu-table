#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION_ID="${OPENCLAW_SESSION_ID:-$(uuidgen)}"
TIMEOUT_SECONDS="${OPENCLAW_AGENT_TIMEOUT:-1800}"
LOG_DIR="${OPENCLAW_INTEL_LOG_DIR:-/Users/tidepang/Library/Logs/feishu-team-intel-openclaw}"

usage() {
  cat <<EOF
Usage:
  bash scripts/ask_openclaw_intel.sh "<natural-language request>"

Examples:
  bash scripts/ask_openclaw_intel.sh "跑一下今天的 pipeline，然后用 4 条 bullet 告诉我结果"
  bash scripts/ask_openclaw_intel.sh "看下当前 workflow 状态"
  bash scripts/ask_openclaw_intel.sh "分析最新周报，给我 5 个更值得写的话题"
EOF
}

if [[ $# -eq 0 ]]; then
  usage
  exit 1
fi

USER_PROMPT="$*"
PREFIX='Use $feishu-team-intel for the Feishu intelligence repo at /Users/tidepang/2026project/feishu-team.'
INSTRUCTIONS="Reuse the local lark-cli auth on this machine. When running pipeline or step commands, set OPENCLAW_INTEL_LOG_DIR=$LOG_DIR so logs are written locally."
MESSAGE="$PREFIX $INSTRUCTIONS User request: $USER_PROMPT"

openclaw agent \
  --local \
  --session-id "$SESSION_ID" \
  --message "$MESSAGE" \
  --json \
  --timeout "$TIMEOUT_SECONDS"
