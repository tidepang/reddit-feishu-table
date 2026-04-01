#!/usr/bin/env python3
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from intel_common import LarkBaseClient, load_json


def summarize_report(markdown: str, max_lines: int = 6) -> str:
    lines: List[str] = []
    for raw in markdown.splitlines():
        text = raw.strip()
        if not text:
            continue
        if text.startswith("#"):
            continue
        lines.append(text)
        if len(lines) >= max_lines:
            break
    summary = " ".join(lines)
    return summary[:500]


def compact_body(markdown: str, max_chars: int = 2800) -> str:
    text = markdown.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rstrip()
    return f"{truncated}\n\n[内容已截断，详版保存在本地 data/ 目录。]"


def top_keywords_text(packet_path: Optional[str]) -> str:
    if not packet_path:
        return ""
    path = Path(packet_path)
    if not path.exists():
        return ""
    with path.open("r", encoding="utf-8") as handle:
        packet = json.load(handle)
    keywords = [item["keyword"] for item in packet.get("top_keywords", [])[:5] if item.get("keyword")]
    return ", ".join(keywords)


def build_payload(title: str, markdown: str, packet_path: Optional[str]) -> Dict:
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "记录类型": "周报",
        "标题": title,
        "采集时间": now_text,
        "来源账号/网站": "自动周报生成",
        "情报摘要": summarize_report(markdown),
        "情报关键词": top_keywords_text(packet_path),
        "周报正文": compact_body(markdown),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a generated weekly report back into Feishu Base.")
    parser.add_argument("--config", required=True, help="Path to config JSON file")
    parser.add_argument("--report-file", required=True, help="Markdown report file to publish")
    parser.add_argument("--packet-file", default=None, help="Optional JSON packet file for top keywords")
    parser.add_argument("--title", default=None, help="Optional custom record title")
    parser.add_argument("--dry-run", action="store_true", help="Print payload instead of writing")
    args = parser.parse_args()

    config = load_json(args.config)
    client = LarkBaseClient(
        base_token=config["base"]["base_token"],
        table_id=config["base"]["table_id"],
        lark_cli_bin=config["collector"].get("lark_cli_bin"),
    )

    report_path = Path(args.report_file)
    with report_path.open("r", encoding="utf-8") as handle:
        markdown = handle.read().strip()

    stamp = datetime.now().strftime("%Y-%m-%d")
    title = args.title or f"电子音乐选题会周报 {stamp}"
    payload = build_payload(title=title, markdown=markdown, packet_path=args.packet_file)

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    result = client.upsert(payload)
    print(json.dumps({"title": title, "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
