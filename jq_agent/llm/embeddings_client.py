"""Embeddings 同步 HTTP 客户端复用（避免每次 embed 新建连接）。"""

from __future__ import annotations

import httpx

from jq_agent.config import Settings
from jq_agent.llm.transport import build_httpx_limits, build_httpx_timeout, use_http2

_sync_clients: dict[str, httpx.Client] = {}


def get_sync_embeddings_client(settings: Settings) -> httpx.Client:
    """按 base_url + key 前缀复用 Client，保持连接热复用。"""
    key = f"{settings.llm_base_url.rstrip('/')}|{settings.llm_api_key[:16]}"
    if key not in _sync_clients:
        _sync_clients[key] = httpx.Client(
            timeout=build_httpx_timeout(settings),
            limits=build_httpx_limits(settings),
            http2=use_http2(settings),
        )
    return _sync_clients[key]
