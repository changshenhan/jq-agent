"""
MCP stdio 服务：将 jq-agent 核心工具暴露给 MCP 宿主（Cursor / Claude 等）。

运行：pip install 'jq-agent[mcp]' && jq-agent mcp-stdio
或：python -m jq_agent.mcp_stdio
"""

from __future__ import annotations

import json
from typing import Any

from jq_agent.config import load_settings
from jq_agent.tools.handlers import ToolDispatcher


def _dispatch(name: str, **kwargs: Any) -> str:
    settings = load_settings()
    d = ToolDispatcher(settings, ui_lang="zh", active_session=None)
    return d.dispatch(name, json.dumps(kwargs, ensure_ascii=False))


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:
        raise SystemExit(
            "需要安装 MCP SDK：pip install 'jq-agent[mcp]' 或 pip install mcp"
        ) from e

    mcp = FastMCP("jq-agent")

    @mcp.tool()
    def query_jq_docs(question: str) -> str:
        """检索 jqdatasdk 官方片段。"""
        return _dispatch("query_jq_docs", question=question)

    @mcp.tool()
    def read_file(path: str) -> str:
        """读取 Agent 工作区内的文本文件。"""
        return _dispatch("read_file", path=path)

    @mcp.tool()
    def lint_strategy_file(path: str) -> str:
        """对沙箱内 .py 运行 ruff check（若已安装）。"""
        return _dispatch("lint_strategy_file", path=path)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
