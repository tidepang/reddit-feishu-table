#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from intel_common import LarkBaseClient, load_json, normalize_text


def parse_topics(markdown: str) -> List[Dict[str, str]]:
    lines = markdown.splitlines()
    in_section = False
    topics: List[Dict[str, str]] = []
    current: Dict[str, str] = {}

    for raw in lines:
        line = raw.strip()
        if line == "## 适合小红书的 10 个选题":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line:
            continue

        title_match = re.match(r"^\d+\.\s+标题：`(.+)`$", line)
        if title_match:
            if current:
                topics.append(current)
            current = {
                "title": title_match.group(1).strip(),
                "angle": "",
                "audience": "",
                "format": "",
            }
            continue

        if not current:
            continue
        if line.startswith("角度："):
            current["angle"] = line.removeprefix("角度：").strip()
        elif line.startswith("适合的目标群体："):
            current["audience"] = line.removeprefix("适合的目标群体：").strip()
        elif line.startswith("建议体裁："):
            current["format"] = line.removeprefix("建议体裁：").strip()

    if current:
        topics.append(current)
    return topics


def build_summary(topic: Dict[str, str]) -> str:
    parts = []
    if topic.get("angle"):
        parts.append(f"角度：{topic['angle']}")
    if topic.get("audience"):
        parts.append(f"目标群体：{topic['audience']}")
    if topic.get("format"):
        parts.append(f"建议体裁：{topic['format']}")
    return " ".join(parts)[:500]


def build_payload(topic: Dict[str, str], score: int) -> Dict:
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    keywords = ["周报选题"]
    if topic.get("format"):
        keywords.append(topic["format"])
    return {
        "记录类型": "自动情报",
        "标题": topic["title"],
        "来源平台": "选题",
        "来源账号/网站": "周报选题生成",
        "采集时间": now_text,
        "情报关键词": ", ".join(keywords),
        "情报摘要": build_summary(topic),
        "情报评分": score,
        "是否转选题": "已选中",
    }


def existing_titles(client: LarkBaseClient, max_scan: int, view_id: str) -> set:
    titles = set()
    for record in client.list_records(max_scan=max_scan, view_id=view_id):
        title = str(record.get("标题") or "").strip()
        if title:
            titles.add(normalize_text(title))
    return titles


def main() -> int:
    parser = argparse.ArgumentParser(description="Write topic candidates from an editorial report into Feishu Base.")
    parser.add_argument("--config", required=True, help="Path to config JSON file")
    parser.add_argument("--report-file", required=True, help="Markdown editorial report file")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads instead of writing")
    args = parser.parse_args()

    config = load_json(args.config)
    report_path = Path(args.report_file)
    markdown = report_path.read_text(encoding="utf-8")
    topics = parse_topics(markdown)

    client = LarkBaseClient(
        base_token=config["base"]["base_token"],
        table_id=config["base"]["table_id"],
        lark_cli_bin=config["collector"].get("lark_cli_bin"),
    )

    seen_titles = existing_titles(
        client,
        max_scan=config["collector"].get("max_existing_scan", 400),
        view_id=config["base"].get("view_id"),
    )

    created = []
    skipped = []
    for index, topic in enumerate(topics, start=1):
        normalized_title = normalize_text(topic["title"])
        if normalized_title in seen_titles:
            skipped.append(topic["title"])
            continue

        payload = build_payload(topic, score=max(60, 95 - (index - 1) * 3))
        if args.dry_run:
            created.append(payload)
        else:
            result = client.upsert(payload)
            created.append({"title": topic["title"], "result": result})
        seen_titles.add(normalized_title)

    print(
        json.dumps(
            {
                "report_file": str(report_path),
                "topics_found": len(topics),
                "created_count": len(created),
                "skipped_count": len(skipped),
                "skipped_titles": skipped,
                "created": created,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
