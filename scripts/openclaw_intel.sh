#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${OPENCLAW_INTEL_CONFIG:-${2:-$ROOT_DIR/config/intel_v1.local.json}}"
COMMAND="${1:-status}"
WINDOW_DAYS="${WINDOW_DAYS:-7}"
TOP_N="${TOP_N:-12}"
LIMIT_PER_SOURCE="${LIMIT_PER_SOURCE:-}"
LOG_DIR="${OPENCLAW_INTEL_LOG_DIR:-}"

enable_file_logging() {
  if [[ -z "$LOG_DIR" || -n "${OPENCLAW_INTEL_LOGGING_ACTIVE:-}" ]]; then
    return
  fi

  mkdir -p "$LOG_DIR"
  local stamp log_file latest_link
  stamp="$(date +%Y%m%d_%H%M%S)"
  log_file="$LOG_DIR/${COMMAND}_${stamp}.log"
  latest_link="$LOG_DIR/latest_${COMMAND}.log"

  export OPENCLAW_INTEL_LOGGING_ACTIVE=1
  exec > >(tee -a "$log_file") 2>&1
  ln -sfn "$log_file" "$latest_link"
  echo "Log file: $log_file"
}

require_config() {
  if [[ ! -f "$CONFIG_PATH" ]]; then
    echo "Config not found: $CONFIG_PATH" >&2
    echo "Copy config/intel_v1.example.json to config/intel_v1.local.json and fill in base token/table/view first." >&2
    exit 1
  fi
}

enable_file_logging

latest_file() {
  local pattern="$1"
  python3 - "$ROOT_DIR" "$pattern" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
pattern = sys.argv[2]
matches = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
print(matches[0] if matches else "")
PY
}

print_status() {
  require_config
  local latest_packet latest_report latest_editorial
  latest_packet="$(latest_file 'data/weekly_packet_*.json')"
  latest_report="$(latest_file 'data/weekly_report_*.md')"
  latest_editorial="$(latest_file 'data/weekly_editorial_report_*.md')"

  cat <<EOF
Repo: $ROOT_DIR
Config: $CONFIG_PATH
Latest packet: ${latest_packet:-none}
Latest report: ${latest_report:-none}
Latest editorial: ${latest_editorial:-none}
EOF
}

run_collect() {
  require_config
  local args=(--config "$CONFIG_PATH" --write)
  if [[ -n "$LIMIT_PER_SOURCE" ]]; then
    args+=(--limit-per-source "$LIMIT_PER_SOURCE")
  fi
  python3 "$ROOT_DIR/scripts/collect_intel_v1.py" "${args[@]}"
}

run_weekly() {
  require_config
  python3 "$ROOT_DIR/scripts/generate_weekly_topic_packet.py" \
    --config "$CONFIG_PATH" \
    --days "$WINDOW_DAYS" \
    --top-n "$TOP_N"
}

run_publish() {
  require_config
  local stamp report packet editorial
  stamp="$(date +%Y%m%d)"
  editorial="$ROOT_DIR/data/weekly_editorial_report_${stamp}.md"
  report="$ROOT_DIR/data/weekly_report_${stamp}.md"
  packet="$ROOT_DIR/data/weekly_packet_${stamp}.json"

  if [[ -f "$editorial" ]]; then
    report="$editorial"
  fi

  python3 "$ROOT_DIR/scripts/publish_weekly_report_to_base.py" \
    --config "$CONFIG_PATH" \
    --report-file "$report" \
    --packet-file "$packet"
}

run_pipeline() {
  require_config
  LIMIT_PER_SOURCE="$LIMIT_PER_SOURCE" WINDOW_DAYS="$WINDOW_DAYS" TOP_N="$TOP_N" \
    bash "$ROOT_DIR/scripts/run_intel_pipeline.sh" "$CONFIG_PATH"
}

run_write_topics() {
  require_config
  local report_file
  report_file="${3:-$(latest_file 'data/weekly_editorial_report_*.md')}"
  if [[ -z "$report_file" ]]; then
    echo "No weekly_editorial_report_*.md file found under $ROOT_DIR/data" >&2
    exit 1
  fi
  python3 "$ROOT_DIR/scripts/write_topics_from_editorial_report.py" \
    --config "$CONFIG_PATH" \
    --report-file "$report_file"
}

case "$COMMAND" in
  status)
    print_status
    ;;
  collect)
    run_collect
    ;;
  weekly)
    run_weekly
    ;;
  publish)
    run_publish
    ;;
  pipeline)
    run_pipeline
    ;;
  write-topics)
    run_write_topics "$@"
    ;;
  *)
    echo "Usage: $0 {status|collect|weekly|publish|pipeline|write-topics} [config-path] [report-file]" >&2
    exit 1
    ;;
esac
