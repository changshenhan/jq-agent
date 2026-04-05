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

    @mcp.tool()
    def list_directory(path: str = "", max_entries: int = 200) -> str:
        """列出沙箱目录下的文件与子目录。"""
        return _dispatch("list_directory", path=path, max_entries=max_entries)

    @mcp.tool()
    def glob_files(pattern: str) -> str:
        """按 glob 枚举沙箱内文件路径。"""
        return _dispatch("glob_files", pattern=pattern)

    @mcp.tool()
    def grep_workspace(
        regex: str,
        file_glob: str = "**/*.py",
        max_matches: int = 40,
    ) -> str:
        """在沙箱内正则搜索代码行。"""
        return _dispatch(
            "grep_workspace",
            regex=regex,
            file_glob=file_glob,
            max_matches=max_matches,
        )

    @mcp.tool()
    def search_replace(path: str, old_string: str, new_string: str) -> str:
        """文件中唯一匹配片段替换。"""
        return _dispatch(
            "search_replace",
            path=path,
            old_string=old_string,
            new_string=new_string,
        )

    @mcp.tool()
    def run_terminal_cmd(command: str) -> str:
        """在沙箱根目录执行命令（strict 模式禁用）。"""
        return _dispatch("run_terminal_cmd", command=command)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
