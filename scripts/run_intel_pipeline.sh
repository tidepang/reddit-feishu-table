#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:-$ROOT_DIR/config/intel_v1.local.json}"
LIMIT_PER_SOURCE="${LIMIT_PER_SOURCE:-}"
WINDOW_DAYS="${WINDOW_DAYS:-7}"
TOP_N="${TOP_N:-12}"

COLLECT_ARGS=(--config "$CONFIG_PATH" --write)
if [[ -n "$LIMIT_PER_SOURCE" ]]; then
  COLLECT_ARGS+=(--limit-per-source "$LIMIT_PER_SOURCE")
fi

python3 "$ROOT_DIR/scripts/collect_intel_v1.py" "${COLLECT_ARGS[@]}"
python3 "$ROOT_DIR/scripts/generate_weekly_topic_packet.py" \
  --config "$CONFIG_PATH" \
  --days "$WINDOW_DAYS" \
  --top-n "$TOP_N"

STAMP="$(date +%Y%m%d)"
EDITORIAL_REPORT="$ROOT_DIR/data/weekly_editorial_report_${STAMP}.md"
DEFAULT_REPORT="$ROOT_DIR/data/weekly_report_${STAMP}.md"
PACKET_FILE="$ROOT_DIR/data/weekly_packet_${STAMP}.json"

REPORT_TO_PUBLISH="$DEFAULT_REPORT"
if [[ -f "$EDITORIAL_REPORT" ]]; then
  REPORT_TO_PUBLISH="$EDITORIAL_REPORT"
fi

python3 "$ROOT_DIR/scripts/publish_weekly_report_to_base.py" \
  --config "$CONFIG_PATH" \
  --report-file "$REPORT_TO_PUBLISH" \
  --packet-file "$PACKET_FILE"
