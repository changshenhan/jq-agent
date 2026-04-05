"""文档索引：GitHub 源码切片 + 可选通过底座模型 Embeddings API 写入向量缓存（无本地嵌入模型）。"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from typing import Any

from jq_agent.config import Settings, load_settings
from jq_agent.indexing.chunk_ast import build_all_chunks
from jq_agent.indexing.fetch_github import fetch_sources
from jq_agent.indexing.paths import cache_src_dir, chunks_json_path, embeddings_json_path, index_meta_path
from jq_agent.llm.embeddings import embed_texts


def build_index(
    *,
    full: bool = False,
    reset: bool = True,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """下载 GitHub 源、AST 切片；可选调用 Embeddings API 生成语义检索用缓存。"""
    s = settings or load_settings()
    src = cache_src_dir()
    paths = fetch_sources(src, full=full)
    chunks = build_all_chunks(src)
    if not chunks:
        return {"error": "no_chunks", "paths": [str(p) for p in paths]}

    idx_root = chunks_json_path().parent
    if reset and idx_root.exists():
        shutil.rmtree(idx_root)
    idx_root.mkdir(parents=True, exist_ok=True)

    rows = [
        {"chunk_id": c.chunk_id, "source": c.source, "version": c.version, "text": c.text}
        for c in chunks
    ]
    chunks_json_path().write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    emb_info: dict[str, Any] = {"written": False}
    if s.llm_api_key.strip():
        try:
            texts = [r["text"] for r in rows]
            all_vec: list[list[float]] = []
            batch = 32
            for i in range(0, len(texts), batch):
                batch_texts = texts[i : i + batch]
                all_vec.extend(embed_texts(batch_texts, s))
            emb_map = {rows[j]["chunk_id"]: all_vec[j] for j in range(len(rows))}
            embeddings_json_path().write_text(json.dumps(emb_map), encoding="utf-8")
            emb_info = {"written": True, "dimensions": len(all_vec[0]) if all_vec else 0}
        except Exception as e:
            emb_info = {"written": False, "error": str(e)}
    else:
        emb_info = {
            "written": False,
            "skipped": True,
            "hint": "设置 JQ_LLM_API_KEY 后重新执行 index build 可生成语义检索缓存",
        }

    meta = {
        "built_at": datetime.now(UTC).isoformat(),
        "index_dir": str(idx_root),
        "chunk_count": len(rows),
        "files": sorted({c.source for c in chunks}),
        "full_mode": full,
        "embeddings": emb_info,
    }
    index_meta_path().write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def index_status() -> dict[str, Any]:
    cp = chunks_json_path()
    ep = embeddings_json_path()
    meta_f = index_meta_path()
    out: dict[str, Any] = {
        "chunks_path": str(cp),
        "chunks_exists": cp.exists(),
        "embeddings_path": str(ep),
        "embeddings_exists": ep.exists(),
        "meta_exists": meta_f.exists(),
    }
    if cp.exists():
        try:
            data = json.loads(cp.read_text(encoding="utf-8"))
            out["chunk_count"] = len(data) if isinstance(data, list) else 0
        except (json.JSONDecodeError, OSError, TypeError):
            out["chunk_count"] = 0
    if meta_f.exists():
        try:
            out["meta"] = json.loads(meta_f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            out["meta_error"] = True
    return out
