"""可选 Web UI：FastAPI + Vite/React 静态资源 + SSE。使用 ``pip install 'jq-agent[web]'`` 安装依赖。"""

from __future__ import annotations

__all__ = ["app", "create_app"]


def __getattr__(name: str) -> object:
    if name in __all__:
        from jq_agent.web import server

        return getattr(server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
