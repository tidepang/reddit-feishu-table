#!/usr/bin/env python3
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from intel_common import LarkBaseClient, load_json, normalize_text


def parse_local_datetime(value: str) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def as_scalar(value):
    if isinstance(value, list):
        if not value:
            return ""
        if len(value) == 1:
            return value[0]
    return value


def clean_url(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.startswith("[") and "](" in text and text.endswith(")"):
        try:
            return text.split("](", 1)[1][:-1]
        except IndexError:
            return text
    return text


def coerce_record(record: Dict) -> Dict:
    cleaned = {key: as_scalar(value) for key, value in record.items()}
    cleaned["score"] = int(cleaned.get("情报评分") or 0)
    cleaned["collected_at"] = parse_local_datetime(cleaned.get("采集时间", ""))
    cleaned["record_type"] = str(cleaned.get("记录类型") or "").strip()
    cleaned["platform"] = str(cleaned.get("来源平台") or "").strip()
    cleaned["source_url"] = clean_url(cleaned.get("来源链接"))
    cleaned["keyword_list"] = [
        token.strip()
        for token in str(cleaned.get("情报关键词", "")).split(",")
        if token.strip()
    ]
    return cleaned


def keep_record(record: Dict) -> bool:
    if normalize_text(record.get("record_type", "")) != "自动情报":
        return False
    if not str(record.get("标题") or "").strip():
        return False
    if not record.get("platform"):
        return False
    if not record.get("source_url"):
        return False
    return True


def filter_recent(records: List[Dict], days: int) -> List[Dict]:
    cutoff = datetime.now() - timedelta(days=days)
    filtered = []
    for record in records:
        if not keep_record(record):
            continue
        collected_at = record.get("collected_at")
        if collected_at is None or collected_at >= cutoff:
            filtered.append(record)
    return filtered


def build_packet(records: List[Dict], days: int, top_n: int) -> Dict:
    filtered = filter_recent(records, days=days)
    filtered.sort(key=lambda item: item.get("score", 0), reverse=True)
    top_records = filtered[:top_n]

    keyword_counter = Counter()
    platform_counter = Counter()
    source_counter = Counter()
    grouped_titles = defaultdict(list)

    for record in filtered:
        for keyword in record.get("keyword_list", []):
            keyword_counter[keyword] += 1
        platform_counter[str(record.get("来源平台", ""))] += 1
        source_counter[str(record.get("来源账号/网站", ""))] += 1

        title = normalize_text(str(record.get("标题", "")))
        if "festival" in title or "tomorrowland" in title or "ultra" in title:
            grouped_titles["festival_live"].append(record["标题"])
        if "producer" in title or "sample" in title or "synth" in title or "ableton" in title:
            grouped_titles["producer_tools"].append(record["标题"])
        if "house" in title or "techno" in title or "artist" in title or "mafia" in title:
            grouped_titles["artist_scene"].append(record["标题"])

    candidate_angles = []
    if grouped_titles["festival_live"]:
        candidate_angles.append(
            {
                "angle": "海外大型电子音乐节与现场 set 热点",
                "evidence_titles": grouped_titles["festival_live"][:5],
                "why_it_matters": "适合转译成小红书上的现场观察、艺人盘点、音乐节趋势内容。",
            }
        )
    if grouped_titles["producer_tools"]:
        candidate_angles.append(
            {
                "angle": "制作人工具链与创作方法",
                "evidence_titles": grouped_titles["producer_tools"][:5],
                "why_it_matters": "适合做入门解释、器材/软件趋势、制作人视角的科普内容。",
            }
        )
    if grouped_titles["artist_scene"]:
        candidate_angles.append(
            {
                "angle": "艺人动态与流派场景变化",
                "evidence_titles": grouped_titles["artist_scene"][:5],
                "why_it_matters": "适合做人物盘点、流派趋势、圈层文化观察。",
            }
        )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "window_days": days,
        "record_count": len(filtered),
        "platform_counts": dict(platform_counter),
        "source_counts": dict(source_counter.most_common(10)),
        "top_keywords": [{"keyword": key, "count": count} for key, count in keyword_counter.most_common(15)],
        "top_records": [
            {
                "title": record.get("标题", ""),
                "platform": record.get("platform", ""),
                "source": record.get("来源账号/网站", ""),
                "url": record.get("source_url", ""),
                "summary": record.get("情报摘要", ""),
                "keywords": record.get("keyword_list", []),
                "score": record.get("score", 0),
                "collected_at": record.get("采集时间", ""),
            }
            for record in top_records
        ],
        "candidate_angles": candidate_angles,
    }


def render_report(packet: Dict) -> str:
    lines = []
    lines.append("# Weekly Intel Report")
    lines.append("")
    lines.append(f"- Generated at: {packet['generated_at']}")
    lines.append(f"- Window: last {packet['window_days']} days")
    lines.append(f"- Signals: {packet['record_count']}")
    lines.append("")

    lines.append("## Platform Counts")
    for platform, count in packet["platform_counts"].items():
        lines.append(f"- {platform}: {count}")
    lines.append("")

    lines.append("## Top Keywords")
    for item in packet["top_keywords"][:10]:
        lines.append(f"- {item['keyword']}: {item['count']}")
    lines.append("")

    lines.append("## Candidate Angles")
    for angle in packet["candidate_angles"]:
        lines.append(f"- {angle['angle']}")
        lines.append(f"  - Why: {angle['why_it_matters']}")
        for title in angle["evidence_titles"]:
            lines.append(f"  - Evidence: {title}")
    lines.append("")

    lines.append("## Top Records")
    for record in packet["top_records"]:
        lines.append(f"- [{record['title']}]({record['url']})")
        lines.append(f"  - Platform: {record['platform']} | Source: {record['source']} | Score: {record['score']}")
        lines.append(f"  - Keywords: {', '.join(record['keywords']) if record['keywords'] else '-'}")
        lines.append(f"  - Summary: {record['summary']}")
    lines.append("")
    return "\n".join(lines)


def render_prompt(packet: Dict, prompt_template: str) -> str:
    payload = json.dumps(packet, ensure_ascii=False, indent=2)
    return f"{prompt_template.strip()}\n\n以下是本周自动情报数据包：\n\n```json\n{payload}\n```"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a weekly topic packet from Feishu auto-intel records.")
    parser.add_argument("--config", required=True, help="Path to config JSON file")
    parser.add_argument("--days", type=int, default=7, help="Rolling window in days")
    parser.add_argument("--top-n", type=int, default=12, help="Number of top records to include")
    parser.add_argument("--output-dir", default="data", help="Directory for generated files")
    parser.add_argument("--view-id", default=None, help="Override view id; defaults to config base.view_id")
    args = parser.parse_args()

    config = load_json(args.config)
    lark_cli_bin = config["collector"].get("lark_cli_bin")
    client = LarkBaseClient(
        base_token=config["base"]["base_token"],
        table_id=config["base"]["table_id"],
        lark_cli_bin=lark_cli_bin,
    )

    records = client.list_records(
        max_scan=config["collector"].get("max_existing_scan", 400),
        view_id=args.view_id or config["base"].get("view_id"),
    )
    coerced = [coerce_record(record) for record in records]
    packet = build_packet(coerced, days=args.days, top_n=args.top_n)

    with open("prompts/weekly_topic_prompt.md", "r", encoding="utf-8") as handle:
        prompt_template = handle.read()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")

    packet_path = output_dir / f"weekly_packet_{stamp}.json"
    report_path = output_dir / f"weekly_report_{stamp}.md"
    prompt_path = output_dir / f"weekly_prompt_{stamp}.md"

    with open(packet_path, "w", encoding="utf-8") as handle:
        json.dump(packet, handle, ensure_ascii=False, indent=2)

    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(render_report(packet))

    with open(prompt_path, "w", encoding="utf-8") as handle:
        handle.write(render_prompt(packet, prompt_template))

    print(
        json.dumps(
            {
                "packet": str(packet_path),
                "report": str(report_path),
                "prompt": str(prompt_path),
                "records": packet["record_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
