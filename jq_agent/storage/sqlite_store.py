"""SQLite 会话存储（Kilo 向：可查询、父子会话树）。"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def db_path() -> Path:
    d = Path.home() / ".jq-agent"
    d.mkdir(parents=True, exist_ok=True)
    return d / "jq_agent.sqlite3"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path()), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                name TEXT PRIMARY KEY,
                parent_name TEXT,
                messages_json TEXT NOT NULL,
                meta_json TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_name)")


def save_messages(
    name: str,
    messages: list[dict[str, Any]],
    *,
    parent_name: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    init_db()
    now = datetime.now(UTC).isoformat()
    with _connect() as c:
        row = c.execute("SELECT parent_name FROM sessions WHERE name = ?", (name,)).fetchone()
        prev_parent = row["parent_name"] if row else None
        eff_parent = parent_name if parent_name is not None else prev_parent
        c.execute("DELETE FROM sessions WHERE name = ?", (name,))
        c.execute(
            """
            INSERT INTO sessions (name, parent_name, messages_json, meta_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                eff_parent,
                json.dumps(messages, ensure_ascii=False),
                json.dumps(meta or {}, ensure_ascii=False),
                now,
            ),
        )


def load_messages(name: str) -> list[dict[str, Any]] | None:
    init_db()
    with _connect() as c:
        row = c.execute(
            "SELECT messages_json FROM sessions WHERE name = ?",
            (name,),
        ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row["messages_json"])
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        return None
    return None


def fork_child(parent_name: str, child_slug: str) -> str:
    safe_parent = "".join(c if c.isalnum() or c in "-_/." else "_" for c in parent_name.strip())[:128]
    safe_child = "".join(c if c.isalnum() or c in "-_" else "_" for c in child_slug.strip())[:64]
    if not safe_child:
        safe_child = "child"
    child_name = f"{safe_parent.rstrip('/')}/{safe_child}"
    init_db()
    with _connect() as c:
        exists = c.execute("SELECT 1 FROM sessions WHERE name = ?", (child_name,)).fetchone()
        if exists:
            return child_name
        now = datetime.now(UTC).isoformat()
        c.execute(
            """
            INSERT INTO sessions (name, parent_name, messages_json, meta_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                child_name,
                safe_parent,
                "[]",
                json.dumps({"forked_from": parent_name}, ensure_ascii=False),
                now,
            ),
        )
    return child_name


def list_session_names() -> list[str]:
    init_db()
    with _connect() as c:
        rows = c.execute("SELECT name FROM sessions ORDER BY updated_at DESC").fetchall()
    return [str(r["name"]) for r in rows]


def session_tree_rows() -> list[dict[str, Any]]:
    init_db()
    with _connect() as c:
        rows = c.execute("SELECT name, parent_name, updated_at FROM sessions ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def import_from_json_if_missing(name: str, json_path: Path) -> bool:
    if load_messages(name) is not None:
        return False
    if not json_path.exists():
        return False
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        msgs = data.get("messages")
        if not isinstance(msgs, list):
            return False
        save_messages(name, msgs, meta={"imported_from": str(json_path)})
        return True
    except (OSError, json.JSONDecodeError):
        return False
