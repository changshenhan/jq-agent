"""基于底座模型 Embeddings API 的语义检索（与关键词检索在 handlers 中混合）。"""

from __future__ import annotations

import json
from typing import Any

from jq_agent.config import Settings
from jq_agent.indexing.paths import chunks_json_path, embeddings_json_path
from jq_agent.llm.embeddings import cosine_similarity, embed_texts

# 进程内缓存：避免每次 query 重复读大 JSON（同一进程多轮对话常见）
_semantic_disk_cache: dict[str, Any] = {
    "emb_mtime_ns": None,
    "chunks_mtime_ns": None,
    "emb_map": None,
    "chunks": None,
}


def _load_cached_semantic_index() -> tuple[dict[str, list[float]], list[dict[str, Any]]] | None:
    ep = embeddings_json_path()
    cp = chunks_json_path()
    if not ep.exists() or not cp.exists():
        return None
    try:
        em_ns = ep.stat().st_mtime_ns
        cm_ns = cp.stat().st_mtime_ns
    except OSError:
        return None
    if (
        _semantic_disk_cache["emb_mtime_ns"] == em_ns
        and _semantic_disk_cache["chunks_mtime_ns"] == cm_ns
        and _semantic_disk_cache["emb_map"] is not None
        and _semantic_disk_cache["chunks"] is not None
    ):
        return _semantic_disk_cache["emb_map"], _semantic_disk_cache["chunks"]
    try:
        emb_map: dict[str, list[float]] = json.loads(ep.read_text(encoding="utf-8"))
        chunks: list[dict[str, Any]] = json.loads(cp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError):
        return None
    _semantic_disk_cache.update(
        {
            "emb_mtime_ns": em_ns,
            "chunks_mtime_ns": cm_ns,
            "emb_map": emb_map,
            "chunks": chunks,
        }
    )
    return emb_map, chunks


def semantic_hits(question: str, settings: Settings, *, top_k: int = 8) -> list[dict[str, Any]]:
    """若已执行 `jq-agent index build` 且配置了 API Key 与 embedding 缓存，则返回语义 Top-K。"""
    if not settings.llm_api_key.strip():
        return []
    loaded = _load_cached_semantic_index()
    if loaded is None:
        return []
    emb_map, chunks = loaded
    if not emb_map or not chunks:
        return []
    try:
        q_emb = embed_texts([question], settings)[0]
    except Exception:
        return []
    scored: list[tuple[float, dict[str, Any]]] = []
    for ch in chunks:
        cid = str(ch.get("chunk_id", ""))
        vec = emb_map.get(cid)
        if not vec:
            continue
        s = cosine_similarity(q_emb, vec)
        scored.append((s, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[dict[str, Any]] = []
    for s, ch in scored[:top_k]:
        out.append(
            {
                "chunk_id": ch.get("chunk_id", ""),
                "source": ch.get("source", ""),
                "version": ch.get("version", ""),
                "text": ch.get("text", ""),
                "score": float(max(0.0, min(1.0, s))),
            }
        )
    return out
