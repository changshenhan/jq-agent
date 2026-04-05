"""单轮子任务 LLM（无工具）— asyncio。"""

from __future__ import annotations

from typing import Any

from jq_agent.config import Settings
from jq_agent.llm.client import AsyncChatClient


async def run_research_subtask_async(settings: Settings, subtask: str, ui_lang: str = "zh") -> str:
    lang_note = "用中文简洁回答。" if ui_lang == "zh" else "Answer concisely in English."
    system = (
        "你是 jq-agent 内置的量化研究子助手，只回答本回合子问题，不调用工具。"
        + lang_note
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": subtask},
    ]
    client = AsyncChatClient(settings)
    try:
        raw = await client.complete(messages, tools=None, tool_choice=None)
    finally:
        await client.aclose()
    choice = (raw.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    return (msg.get("content") or "").strip() or "(empty)"
