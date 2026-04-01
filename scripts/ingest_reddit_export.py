#!/usr/bin/env python3
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from typing import Dict, List

from intel_common import LarkBaseClient, load_json, normalize_text, normalize_url


def build_existing_keys(records: List[dict]) -> Dict[str, set]:
    links = set()
    titles = set()
    for record in records:
        link = record.get("来源链接")
        title = record.get("标题")
        if isinstance(link, str) and link.strip():
            links.add(normalize_url(link))
        if isinstance(title, str) and title.strip():
            titles.add(normalize_text(title))
    return {"links": links, "titles": titles}


def score_reddit_item(item: dict, keywords: List[str]) -> int:
    score = int(item.get("score", 0) or 0)
    comments = int(item.get("num_comments", 0) or 0)
    engagement = min(35, score // 20 + comments // 10)

    created = item.get("created_utc")
    freshness = 8
    if created:
        created_dt = datetime.fromtimestamp(float(created), tz=timezone.utc)
        age_days = (datetime.now(timezone.utc) - created_dt).total_seconds() / 86400
        if age_days <= 3:
            freshness = 25
        elif age_days <= 7:
            freshness = 18
        elif age_days <= 30:
            freshness = 10
        else:
            freshness = 4

    title = normalize_text(item.get("title", ""))
    relevance_terms = [normalize_text(term) for term in keywords if normalize_text(term)]
    relevance = min(40, sum(8 for term in relevance_terms if term in title))
    return min(100, relevance + freshness + engagement)


def to_feishu_record(item: dict, keywords: List[str]) -> dict:
    created = item.get("created_utc")
    if created:
        collected = datetime.fromtimestamp(float(created), tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    else:
        collected = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

    summary = (item.get("selftext") or item.get("summary") or "").strip()
    summary = " ".join(summary.split())[:500]

    matched_keywords = []
    title = normalize_text(item.get("title", ""))
    for term in keywords:
        if term in title:
            matched_keywords.append(term)

    return {
        "记录类型": "自动情报",
        "标题": item.get("title", "").strip(),
        "来源平台": "Reddit",
        "来源链接": item.get("url", "").strip(),
        "来源账号/网站": f"r/{item.get('subreddit', '').strip()}",
        "采集时间": collected,
        "情报关键词": ", ".join(matched_keywords),
        "情报摘要": summary or f"作者 u/{item.get('author', 'unknown')}，score={item.get('score', 0)}，comments={item.get('num_comments', 0)}",
        "情报评分": score_reddit_item(item, keywords),
        "是否转选题": "待判断",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest a Reddit export JSON file into Feishu Base.")
    parser.add_argument("--config", required=True, help="Path to config JSON file")
    parser.add_argument("--input", required=True, help="Path to Reddit export JSON")
    parser.add_argument("--dry-run", action="store_true", help="Print records instead of writing")
    parser.add_argument("--write", action="store_true", help="Write records to Feishu Base")
    args = parser.parse_args()

    if not args.dry_run and not args.write:
        args.dry_run = True

    config = load_json(args.config)
    topic_keywords = [str(item).strip() for item in config.get("keywords", []) if str(item).strip()]
    items = load_json(args.input)
    if not isinstance(items, list):
        raise SystemExit("Reddit export must be a JSON array")

    lark_cli_bin = config["collector"].get("lark_cli_bin") or shutil.which("lark-cli") or "lark-cli"
    client = LarkBaseClient(
        base_token=config["base"]["base_token"],
        table_id=config["base"]["table_id"],
        lark_cli_bin=lark_cli_bin,
    )
    existing = build_existing_keys(client.list_records(max_scan=config["collector"].get("max_existing_scan", 400)))

    prepared = []
    for item in items:
        record = to_feishu_record(item, topic_keywords)
        link_key = normalize_url(record["来源链接"])
        title_key = normalize_text(record["标题"])
        if not record["标题"] or not record["来源链接"]:
            continue
        if link_key in existing["links"] or title_key in existing["titles"]:
            continue
        prepared.append(record)
        existing["links"].add(link_key)
        existing["titles"].add(title_key)

    if args.dry_run:
        print(json.dumps({"count": len(prepared), "records": prepared}, ensure_ascii=False, indent=2))
        return 0

    written = []
    for record in prepared:
        written.append(client.upsert(record))
    print(json.dumps({"count": len(written), "results": written}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
