"""用量审计（轻量）：追加写入 ~/.jq-agent/usage.jsonl。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def usage_log_path() -> Path:
    d = Path.home() / ".jq-agent"
    d.mkdir(parents=True, exist_ok=True)
    return d / "usage.jsonl"


def append_usage(record: dict[str, Any]) -> None:
    line = json.dumps(
        {"ts": datetime.now(UTC).isoformat(), **record},
        ensure_ascii=False,
    )
    with usage_log_path().open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def extract_usage_from_response(raw: dict[str, Any]) -> dict[str, Any]:
    u = raw.get("usage")
    if isinstance(u, dict):
        return {
            "prompt_tokens": u.get("prompt_tokens"),
            "completion_tokens": u.get("completion_tokens"),
            "total_tokens": u.get("total_tokens"),
        }
    return {}
