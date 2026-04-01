#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
from typing import Dict, List, Optional, Sequence


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def normalize_url(url: str) -> str:
    return (url or "").strip().rstrip("/")


class LarkBaseClient:
    def __init__(self, base_token: str, table_id: str, lark_cli_bin: Optional[str] = None) -> None:
        self.base_token = base_token
        self.table_id = table_id
        self.lark_cli_bin = lark_cli_bin or shutil.which("lark-cli") or "lark-cli"

    def _run(self, extra_args: Sequence[str]) -> dict:
        env = os.environ.copy()
        cli_dir = os.path.dirname(self.lark_cli_bin)
        if cli_dir:
            env["PATH"] = f"{cli_dir}:{env.get('PATH', '')}"
        result = subprocess.run(
            [self.lark_cli_bin, "base", *extra_args],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "lark-cli failed")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Unexpected lark-cli output: {result.stdout}") from exc

    def list_records(self, max_scan: int = 400, view_id: Optional[str] = None, include_record_id: bool = False) -> List[Dict]:
        records: List[Dict] = []
        offset = 0
        remaining = max_scan
        while remaining > 0:
            limit = min(50, remaining)
            args = [
                "+record-list",
                "--as",
                "user",
                "--base-token",
                self.base_token,
                "--table-id",
                self.table_id,
                "--limit",
                str(limit),
                "--offset",
                str(offset),
            ]
            if view_id:
                args.extend(["--view-id", view_id])
            payload = self._run(args)
            data = payload["data"]
            fields = data["fields"]
            rows = data["data"]
            record_ids = data.get("record_id_list") or []
            for index, row in enumerate(rows):
                record = dict(zip(fields, row))
                if include_record_id and index < len(record_ids):
                    record["_record_id"] = record_ids[index]
                records.append(record)
            if not data.get("has_more"):
                break
            offset += len(rows)
            remaining -= len(rows)
            if not rows:
                break
        return records

    def upsert(self, record: dict) -> dict:
        return self._run(
            [
                "+record-upsert",
                "--as",
                "user",
                "--base-token",
                self.base_token,
                "--table-id",
                self.table_id,
                "--json",
                json.dumps(record, ensure_ascii=False),
            ]
        )
