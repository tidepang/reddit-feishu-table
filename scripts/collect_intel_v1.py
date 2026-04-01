#!/usr/bin/env python3
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Sequence

from intel_common import LarkBaseClient, load_json, normalize_text, normalize_url

def strip_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        dt = None
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_feishu_datetime(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def fetch_text(url: str, user_agent: str, timeout: int) -> str:
    curl = shutil.which("curl")
    if curl:
        result = subprocess.run(
            [
                curl,
                "-L",
                "--silent",
                "--show-error",
                "--max-time",
                str(timeout),
                "--user-agent",
                user_agent,
                url,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/rss+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def first_text(node: ET.Element, names: Sequence[str]) -> str:
    for name in names:
        child = node.find(name)
        if child is not None and child.text:
            return child.text.strip()
    return ""


@dataclass
class Signal:
    title: str
    link: str
    source_name: str
    platform: str
    published_at: Optional[datetime]
    summary: str
    keywords: List[str]
    score: int

    def to_feishu_payload(self) -> dict:
        collected_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "记录类型": "自动情报",
            "标题": self.title,
            "来源平台": self.platform,
            "来源链接": self.link,
            "来源账号/网站": self.source_name,
            "采集时间": collected_at,
            "情报关键词": ", ".join(self.keywords),
            "情报摘要": self.summary,
            "情报评分": self.score,
            "是否转选题": "待判断",
        }
        return payload

def collect_rss_source(source: dict, keywords: List[str], timeout: int, user_agent: str, limit_override: Optional[int]) -> List[Signal]:
    raw = fetch_text(source["url"], user_agent=user_agent, timeout=timeout)
    root = ET.fromstring(raw)
    items = root.findall(".//channel/item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    limit = limit_override or source.get("limit") or 10
    signals: List[Signal] = []
    for item in items[:limit]:
        title = first_text(item, ["title", "{http://www.w3.org/2005/Atom}title"])
        link = first_text(item, ["link", "{http://www.w3.org/2005/Atom}link"])
        if not link:
            atom_link = item.find("{http://www.w3.org/2005/Atom}link")
            if atom_link is not None:
                link = atom_link.attrib.get("href", "").strip()
        description = first_text(
            item,
            [
                "description",
                "{http://purl.org/rss/1.0/modules/content/}encoded",
                "{http://www.w3.org/2005/Atom}summary",
            ],
        )
        published_raw = first_text(item, ["pubDate", "{http://www.w3.org/2005/Atom}updated", "{http://www.w3.org/2005/Atom}published"])
        published_at = parse_datetime(published_raw)
        summary = strip_html(description)
        matched_keywords = match_keywords(f"{title} {summary}", keywords)
        score = score_web_signal(title=title, summary=summary, matched_keywords=matched_keywords, published_at=published_at)
        if matched_keywords and score >= 1:
            signals.append(
                Signal(
                    title=title,
                    link=link,
                    source_name=source["name"],
                    platform=source["platform"],
                    published_at=published_at,
                    summary=summary[:500],
                    keywords=matched_keywords,
                    score=score,
                )
            )
    return signals


def match_keywords(text: str, keywords: Sequence[str]) -> List[str]:
    normalized = normalize_text(text)
    matches = []
    for keyword in keywords:
        if keyword.lower() in normalized:
            matches.append(keyword)
    return matches


def score_web_signal(title: str, summary: str, matched_keywords: List[str], published_at: Optional[datetime]) -> int:
    relevance = min(45, len(matched_keywords) * 10)

    freshness = 8
    if published_at is not None:
        now = datetime.now(timezone.utc)
        age_days = (now - published_at).total_seconds() / 86400
        if age_days <= 3:
            freshness = 25
        elif age_days <= 7:
            freshness = 18
        elif age_days <= 30:
            freshness = 10
        else:
            freshness = 4

    usefulness_terms = [
        "top",
        "best",
        "guide",
        "how",
        "why",
        "trend",
        "explained",
        "analysis",
        "case study",
        "workflow",
        "tool",
        "launch",
        "report",
        "review",
        "tutorial",
        "insight",
    ]
    usefulness = 8
    normalized = normalize_text(f"{title} {summary}")
    hits = sum(1 for term in usefulness_terms if term in normalized)
    if hits >= 3:
        usefulness = 25
    elif hits == 2:
        usefulness = 18
    elif hits == 1:
        usefulness = 12

    return min(100, relevance + freshness + usefulness)


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect web intelligence signals and write them into Feishu Base.")
    parser.add_argument("--config", required=True, help="Path to config JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Print records instead of writing")
    parser.add_argument("--write", action="store_true", help="Write records to Feishu Base")
    parser.add_argument("--limit-per-source", type=int, default=None, help="Override per-source fetch limit")
    args = parser.parse_args()

    if not args.dry_run and not args.write:
        args.dry_run = True

    config = load_json(args.config)
    lark_cli_bin = config["collector"].get("lark_cli_bin") or shutil.which("lark-cli") or "lark-cli"
    client = LarkBaseClient(
        base_token=config["base"]["base_token"],
        table_id=config["base"]["table_id"],
        lark_cli_bin=lark_cli_bin,
    )

    existing = client.list_records(max_scan=config["collector"].get("max_existing_scan", 400))
    existing_keys = build_existing_keys(existing)

    all_signals: List[Signal] = []
    for source in config["sources"]:
        if source.get("kind") != "rss":
            continue
        signals = collect_rss_source(
            source=source,
            keywords=config["keywords"],
            timeout=config["collector"].get("timeout_seconds", 20),
            user_agent=config["collector"].get("user_agent", "feishu-team-intel-v1/0.1"),
            limit_override=args.limit_per_source,
        )
        all_signals.extend(signals)

    min_score = config["collector"].get("min_score", 45)
    prepared: List[dict] = []
    for signal in sorted(all_signals, key=lambda item: item.score, reverse=True):
        normalized_link = normalize_url(signal.link)
        normalized_title = normalize_text(signal.title)
        if normalized_link in existing_keys["links"] or normalized_title in existing_keys["titles"]:
            continue
        if signal.score < min_score:
            continue
        payload = signal.to_feishu_payload()
        prepared.append(payload)
        existing_keys["links"].add(normalized_link)
        existing_keys["titles"].add(normalized_title)

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
