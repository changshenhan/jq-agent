"""HTTP 传输参数：对齐业界降低延迟的常见做法（HTTP/2、连接池、分阶段超时）。"""

from __future__ import annotations

import httpx

from jq_agent.config import Settings


def http2_available() -> bool:
    try:
        import h2  # noqa: F401
    except ImportError:
        return False
    return True


def build_httpx_timeout(settings: Settings) -> httpx.Timeout:
    """connect 与 read 分离：连接慢时快速失败，长生成时仍给足 read。"""
    return httpx.Timeout(
        connect=settings.llm_http_connect_timeout,
        read=settings.llm_http_read_timeout,
        write=min(120.0, settings.llm_http_read_timeout),
        pool=10.0,
    )


def build_httpx_limits(settings: Settings) -> httpx.Limits:
    """提高 keep-alive 复用，减少 TLS 握手与 TCP 建连次数（多轮 Agent 尤其明显）。"""
    return httpx.Limits(
        max_keepalive_connections=settings.llm_http_keepalive,
        max_connections=settings.llm_http_max_connections,
    )


def use_http2(settings: Settings) -> bool:
    return bool(settings.llm_http2) and http2_available()
