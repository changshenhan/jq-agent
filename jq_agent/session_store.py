"""会话持久化：JSON 文件或 SQLite（JQ_SESSION_BACKEND）。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jq_agent.config import load_settings


def sessions_root() -> Path:
    d = Path.home() / ".jq-agent" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def session_path(name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name.strip())[:128]
    if not safe:
        safe = "default"
    return sessions_root() / f"{safe}.json"


def _use_sqlite() -> bool:
    return load_settings().session_backend == "sqlite"


def load_session_messages(name: str) -> list[dict[str, Any]] | None:
    if _use_sqlite():
        from jq_agent.storage import sqlite_store

        sqlite_store.init_db()
        p = session_path(name)
        if sqlite_store.load_messages(name) is None:
            sqlite_store.import_from_json_if_missing(name, p)
        return sqlite_store.load_messages(name)

    p = session_path(name)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        msgs = data.get("messages")
        if isinstance(msgs, list):
            return msgs
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return None


def save_session(name: str, messages: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> Path:
    if _use_sqlite():
        from jq_agent.storage import sqlite_store

        sqlite_store.save_messages(name, messages, meta=meta)
        return Path(sqlite_store.db_path())

    p = session_path(name)
    payload = {
        "version": 1,
        "saved_at": datetime.now(UTC).isoformat(),
        "messages": messages,
        "meta": meta or {},
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def list_sessions() -> list[str]:
    json_names = {p.stem for p in sessions_root().glob("*.json")} if sessions_root().exists() else set()
    if _use_sqlite():
        from jq_agent.storage import sqlite_store

        sqlite_store.init_db()
        sql_names = set(sqlite_store.list_session_names())
        return sorted(sql_names | json_names)
    return sorted(json_names)


def session_tree() -> list[dict[str, Any]]:
    """仅 SQLite 后端有完整父子信息；JSON 模式返回空列表。"""
    if not _use_sqlite():
        return []
    from jq_agent.storage import sqlite_store

    sqlite_store.init_db()
    return sqlite_store.session_tree_rows()
