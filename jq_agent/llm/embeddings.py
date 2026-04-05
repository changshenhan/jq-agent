"""OpenAI 兼容的 Embeddings HTTP API（底座模型提供方），无本地嵌入模型。"""

from __future__ import annotations

import math
from typing import Any

from jq_agent.config import Settings
from jq_agent.llm.embeddings_client import get_sync_embeddings_client


def embed_texts(texts: list[str], settings: Settings) -> list[list[float]]:
    """POST {base}/embeddings，返回与 texts 等长的向量列表。"""
    if not texts:
        return []
    url = settings.llm_base_url.rstrip("/") + "/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {"model": settings.embedding_model, "input": texts}
    client = get_sync_embeddings_client(settings)
    r = client.post(url, headers=headers, json=body)
    r.raise_for_status()
    data = r.json()
    items = data.get("data") or []
    sorted_items = sorted(items, key=lambda x: int(x.get("index", 0)))
    return [list(x["embedding"]) for x in sorted_items]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return dot / (na * nb)
