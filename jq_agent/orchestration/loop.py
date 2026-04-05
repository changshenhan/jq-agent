from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from jq_agent.config import Settings
from jq_agent.i18n import UiLang, t
from jq_agent.llm.client import AsyncChatClient
from jq_agent.llm.streaming import stream_complete_async
from jq_agent.orchestration.task_route import effective_jq_sdk_fast_path
from jq_agent.prompts.jq_sdk_fast_path import jq_sdk_fast_path_addon
from jq_agent.prompts.router import model_system_addon
from jq_agent.prompts.system import SYSTEM_PROMPT
from jq_agent.retrieval.linkage import system_prompt_retrieval_addon
from jq_agent.session_compact import maybe_compact
from jq_agent.session_store import load_session_messages, save_session
from jq_agent.tools.handlers import ToolDispatcher
from jq_agent.tools.metrics_rich import print_metrics_summary
from jq_agent.tools.registry import openai_tools
from jq_agent.usage_log import append_usage, extract_usage_from_response


@dataclass
class AgentResult:
    messages: list[dict[str, Any]] = field(default_factory=list)
    stopped_reason: str = ""
    iterations: int = 0
    usage_records: list[dict[str, Any]] = field(default_factory=list)


def format_stopped_reason(code: str, ui_lang: UiLang, max_iter: int) -> str:
    if code.startswith("missing_api_key"):
        return t("reason_missing_key", ui_lang)
    if code == "completed_no_tool_calls":
        return t("reason_done", ui_lang)
    if code.startswith("max_iterations_reached"):
        return f"{t('reason_max_iter', ui_lang)} ({max_iter})"
    if code.startswith("llm_error:"):
        detail = code.removeprefix("llm_error:")
        return t("reason_llm_error", ui_lang, detail=detail)
    return code


def _sum_total_tokens(usage_accum: list[dict[str, Any]]) -> int:
    n = 0
    for u in usage_accum:
        t = u.get("total_tokens")
        if isinstance(t, int):
            n += t
    return n


def _iteration_status_panel(
    task_goal: str,
    cur_iter: int,
    max_iter: int,
    usage_accum: list[dict[str, Any]],
    ui_lang: UiLang,
) -> Panel:
    goal = task_goal if len(task_goal) <= 120 else task_goal[:117] + "…"
    tok = _sum_total_tokens(usage_accum)
    tok_str = str(tok) if tok else "—"

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="cyan", justify="right", no_wrap=True)
    grid.add_column()
    if ui_lang == "zh":
        grid.add_row("任务目标", goal)
        grid.add_row("已用步数", f"{cur_iter} / {max_iter}")
        grid.add_row("消耗 Token", tok_str)
        title = "运行状态"
    else:
        grid.add_row("Goal", goal)
        grid.add_row("Step", f"{cur_iter} / {max_iter}")
        grid.add_row("Tokens", tok_str)
        title = "Status"

    return Panel(grid, title=title, border_style="blue")


def _ide_system_addon(settings: Settings) -> str:
    if not settings.ide_agent_tools:
        return ""
    return (
        "IDE Agent 补充（对齐 Kilocode「工作区浏览 + 终端执行」思路；路径均在沙箱 `.jq-agent` 内）：\n"
        "- **list_directory** / **glob_files** / **grep_workspace**：探索目录、按 glob 列文件、正则搜代码行。\n"
        "- **search_replace**：对 **唯一匹配** 片段做局部替换（优先于整文件 **write_strategy_file**）。\n"
        "- **run_terminal_cmd**：在沙箱根目录执行单行命令（`shlex` 解析；**JQ_PERMISSION_MODE=strict** 时禁用）。\n"
        "量化主路径不变：**query_jq_docs** → 写改策略 → **lint_strategy_file** → "
        "**execute_backtest** → **analyze_backtest_metrics**。"
    )


def _build_system_content(settings: Settings, ui_lang: UiLang, user_prompt: str) -> str:
    parts = [
        SYSTEM_PROMPT.strip(),
        model_system_addon(settings.model, settings.llm_base_url),
        system_prompt_retrieval_addon(ui_lang),
    ]
    ide = _ide_system_addon(settings)
    if ide:
        parts.append(ide)
    if effective_jq_sdk_fast_path(settings, user_prompt):
        parts.append(jq_sdk_fast_path_addon(ui_lang))
    return "\n\n".join(parts)


async def gather_tool_results(
    dispatcher: ToolDispatcher,
    tool_calls: list[dict[str, Any]],
    console: Console | None = None,
) -> list[tuple[str, str, str]]:
    """asyncio.gather + asyncio.to_thread，保持 tool_calls 顺序。"""
    c = console or Console()

    async def one(tc: dict[str, Any]) -> tuple[str, str, str]:
        fn = tc.get("function") or {}
        name = fn.get("name", "")
        args = fn.get("arguments", "")
        tid = tc.get("id", "")
        if name == "execute_backtest":
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=c,
                transient=True,
            ) as progress:
                progress.add_task("正在执行回测…", total=None)
                out = await asyncio.to_thread(dispatcher.dispatch, name, args)
        elif name == "run_terminal_cmd":
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=c,
                transient=True,
            ) as progress:
                progress.add_task("正在执行终端命令…", total=None)
                out = await asyncio.to_thread(dispatcher.dispatch, name, args)
        else:
            out = await asyncio.to_thread(dispatcher.dispatch, name, args)
        return tid, name, out

    return list(await asyncio.gather(*[one(tc) for tc in tool_calls]))


async def run_agent_loop(
    user_prompt: str,
    settings: Settings,
    console: Console | None = None,
    *,
    ui_lang: UiLang = "zh",
    session_name: str | None = None,
    resume_session: bool = False,
    log_callback: Callable[[str], None] | None = None,
) -> AgentResult:
    """Plan → Execute → Observe：全链路 asyncio。

    若提供 log_callback，则使用带 record 的 Console 将每次输出导出为纯文本并回调（用于 Web SSE）；
    此时忽略传入的 console。
    """
    if log_callback is not None:
        c = Console(record=True, width=120, force_terminal=False)
    elif console is not None:
        c = console
    else:
        c = Console()

    def emit_print(*objects: Any, **kwargs: Any) -> None:
        c.print(*objects, **kwargs)
        if log_callback is not None:
            log_callback(c.export_text(clear=True))

    if not settings.llm_api_key.strip():
        if log_callback is not None:
            log_callback("未配置 JQ_LLM_API_KEY，无法调用模型。\n")
        return AgentResult(
            messages=[],
            stopped_reason="missing_api_key",
            iterations=0,
        )

    client = AsyncChatClient(settings)
    dispatcher = ToolDispatcher(
        settings,
        ui_lang=ui_lang,
        active_session=session_name,
    )
    tools = openai_tools(
        ide_agent=settings.ide_agent_tools,
        github_tools=settings.github_tools_enabled,
    )
    system_full = _build_system_content(settings, ui_lang, user_prompt)

    if session_name and resume_session:
        loaded = load_session_messages(session_name)
        if loaded and len(loaded) >= 1:
            messages = list(loaded)
            messages[0] = {"role": "system", "content": system_full}
            messages.append({"role": "user", "content": user_prompt})
        else:
            messages = [
                {"role": "system", "content": system_full},
                {"role": "user", "content": user_prompt},
            ]
    else:
        messages = [
            {"role": "system", "content": system_full},
            {"role": "user", "content": user_prompt},
        ]

    result = AgentResult(messages=messages)
    usage_accum: list[dict[str, Any]] = []
    task_goal = user_prompt.strip() or "(empty)"

    try:
        for i in range(settings.max_iterations):
            result.iterations = i + 1
            emit_print(
                _iteration_status_panel(
                    task_goal,
                    result.iterations,
                    settings.max_iterations,
                    usage_accum,
                    ui_lang,
                )
            )

            messages = await maybe_compact(messages, settings, client)

            try:
                if settings.llm_stream:
                    raw, stream_text, u_extra = await stream_complete_async(
                        client, messages, tools, "auto"
                    )
                    if stream_text:
                        emit_print(stream_text)
                    if u_extra and settings.usage_log:
                        usage_accum.append(u_extra)
                        append_usage({"phase": "llm_stream", "model": settings.model, **u_extra})
                else:
                    raw = await client.complete(messages, tools=tools, tool_choice="auto")
                    u = extract_usage_from_response(raw)
                    if u and settings.usage_log:
                        usage_accum.append(u)
                        append_usage({"phase": "llm", "model": settings.model, **u})
            except Exception as e:
                result.messages = messages
                result.stopped_reason = f"llm_error:{e}"
                result.usage_records = usage_accum
                return result

            choice = (raw.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            messages.append(message)

            tool_calls = message.get("tool_calls") or []
            content = message.get("content") or ""
            if tool_calls and content and not settings.llm_stream:
                emit_print(content)

            if not tool_calls:
                if content and not settings.llm_stream:
                    emit_print(content)
                result.messages = messages
                result.stopped_reason = "completed_no_tool_calls"
                result.usage_records = usage_accum
                if session_name:
                    save_session(session_name, messages)
                return result

            batch = await gather_tool_results(dispatcher, tool_calls, console=c)
            for tid, name, tool_out in batch:
                lbl = t("tool_line", ui_lang)
                emit_print(f"[cyan]{lbl}[/cyan] {name}(…)")
                if name == "analyze_backtest_metrics":
                    print_metrics_summary(c, tool_out)
                    if log_callback is not None:
                        log_callback(c.export_text(clear=True))
                emit_print(f"[dim]{tool_out[:2000]}{'…' if len(tool_out) > 2000 else ''}[/dim]")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tid,
                        "content": tool_out,
                    }
                )

        result.messages = messages
        result.stopped_reason = f"max_iterations_reached:{settings.max_iterations}"
        result.usage_records = usage_accum
        if session_name:
            save_session(session_name, messages)
        return result
    finally:
        await client.aclose()
