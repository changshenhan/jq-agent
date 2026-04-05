"""终端工具阶段文案（借鉴 Open Harness harness-loop：按工具名更新进度提示）。"""

from __future__ import annotations

from jq_agent.i18n import UiLang

# 常见工具：与 registry 中的名称一致
_SPINNER_ZH: dict[str, str] = {
    "query_jq_docs": "检索 jqdatasdk 文档…",
    "read_file": "读取文件…",
    "write_strategy_file": "写入策略文件…",
    "search_replace": "编辑文件…",
    "execute_backtest": "正在执行回测…",
    "analyze_backtest_metrics": "解析回测指标…",
    "lint_strategy_file": "运行 ruff 检查…",
    "research_subtask": "子任务推理…",
    "fork_subagent_session": "分叉会话…",
    "list_directory": "列出目录…",
    "glob_files": "枚举文件…",
    "grep_workspace": "搜索工作区…",
    "run_terminal_cmd": "正在执行终端命令…",
    "github_search_repositories": "GitHub 搜索仓库…",
    "github_search_users": "GitHub 搜索用户…",
    "github_get_user": "GitHub 用户信息…",
    "github_get_repository": "GitHub 仓库信息…",
}

_SPINNER_EN: dict[str, str] = {
    "query_jq_docs": "Querying jqdatasdk docs…",
    "read_file": "Reading file…",
    "write_strategy_file": "Writing strategy file…",
    "search_replace": "Editing file…",
    "execute_backtest": "Running backtest…",
    "analyze_backtest_metrics": "Parsing backtest metrics…",
    "lint_strategy_file": "Running ruff…",
    "research_subtask": "Research subtask…",
    "fork_subagent_session": "Forking session…",
    "list_directory": "Listing directory…",
    "glob_files": "Globbing files…",
    "grep_workspace": "Searching workspace…",
    "run_terminal_cmd": "Running shell command…",
    "github_search_repositories": "GitHub repo search…",
    "github_search_users": "GitHub user search…",
    "github_get_user": "GitHub user…",
    "github_get_repository": "GitHub repository…",
}


def tool_spinner_message(tool_name: str, ui_lang: UiLang) -> str:
    """单工具调用时 Rich Progress 上显示的一行说明。"""
    table = _SPINNER_ZH if ui_lang == "zh" else _SPINNER_EN
    if tool_name in table:
        return table[tool_name]
    if ui_lang == "zh":
        return f"运行工具 {tool_name}…"
    return f"Running {tool_name}…"


def parallel_tools_label(count: int, ui_lang: UiLang) -> str:
    """并行多工具时的一条总提示（避免多路 Progress 互相打断）。"""
    if ui_lang == "zh":
        return f"并行执行 {count} 个工具…"
    return f"Running {count} tools in parallel…"
