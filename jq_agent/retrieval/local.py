from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from jq_agent.config import Settings


@dataclass
class DocHit:
    chunk_id: str
    source: str
    version: str
    text: str
    score: float


def load_chunks(path: Path | None = None) -> list[dict[str, Any]]:
    if path is not None:
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        raw = resources.files("jq_agent.data").joinpath("doc_chunks.json").read_text(encoding="utf-8")
        return json.loads(raw)
    except (FileNotFoundError, TypeError, ValueError, OSError):
        pass
    fallback = Path(__file__).resolve().parent.parent / "data" / "doc_chunks.json"
    if not fallback.exists():
        return []
    return json.loads(fallback.read_text(encoding="utf-8"))


def load_merged_chunks(settings: Settings | None = None) -> list[dict[str, Any]]:
    """内置 doc_chunks + 用户 `jq-agent index build` 生成的切片（若存在）。"""
    base = list(load_chunks())
    try:
        from jq_agent.indexing.paths import chunks_json_path

        p = chunks_json_path(settings)
        if not p.exists():
            return base
        extra: list[dict[str, Any]] = json.loads(p.read_text(encoding="utf-8"))
        for row in extra:
            base.append(
                {
                    "id": row.get("chunk_id", ""),
                    "source": row.get("source", ""),
                    "version": row.get("version", ""),
                    "text": row.get("text", ""),
                }
            )
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        pass
    return base


def keyword_search(question: str, chunks: list[dict[str, Any]], top_k: int = 5) -> list[DocHit]:
    """轻量混合检索 MVP：关键词重叠评分；可替换为向量库。"""
    q = question.lower()
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", q)
    if not tokens:
        tokens = [q]
    hits: list[DocHit] = []
    for ch in chunks:
        text = (ch.get("text") or "").lower()
        score = sum(1.0 for t in tokens if t in text)
        if score > 0:
            hits.append(
                DocHit(
                    chunk_id=ch.get("id", ""),
                    source=ch.get("source", ""),
                    version=ch.get("version", ""),
                    text=ch.get("text", ""),
                    score=score,
                )
            )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]
