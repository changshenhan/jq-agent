"""对话压缩（compaction）：超长历史摘要为一条 system 附注，保留尾部若干轮。"""

from __future__ import annotations

import json
from typing import Any

from jq_agent.config import Settings
from jq_agent.llm.client import AsyncChatClient


async def compact_messages(
    messages: list[dict[str, Any]],
    settings: Settings,
    client: AsyncChatClient,
    *,
    keep_last: int,
) -> list[dict[str, Any]]:
    """
    保留首条 system 与最后 keep_last 条；中间部分经 LLM 摘要后写入 system 附加段。
    """
    if len(messages) <= 2 + keep_last:
        return messages
    system = messages[0]
    tail = messages[-keep_last:]
    middle = messages[1:-keep_last]
    if not middle:
        return messages

    brief = _messages_to_brief(middle)
    summarize_prompt = (
        "请将以下对话片段压缩为一段中文技术摘要（量化/jqdatasdk 上下文），"
        "保留关键决策、工具结果要点、错误与数字，不超过 800 字：\n\n" + brief
    )
    raw = await client.complete(
        [
            {"role": "system", "content": "你是会话压缩助手，只输出摘要正文。"},
            {"role": "user", "content": summarize_prompt},
        ],
        tools=None,
        tool_choice=None,
    )
    choice = (raw.get("choices") or [{}])[0]
    summary = (choice.get("message") or {}).get("content") or ""
    summary = summary.strip() or "(摘要为空)"

    new_system_content = (
        str(system.get("content", ""))
        + "\n\n[COMPACTED_HISTORY]\n"
        + summary
    )
    new_system = {**system, "content": new_system_content}
    return [new_system, *tail]


def _messages_to_brief(msgs: list[dict[str, Any]], max_chars: int = 12000) -> str:
    lines: list[str] = []
    for m in msgs:
        role = m.get("role", "")
        content = m.get("content")
        if content is None:
            content = json.dumps(m.get("tool_calls") or [], ensure_ascii=False)[:2000]
        lines.append(f"{role}: {str(content)[:4000]}")
    text = "\n---\n".join(lines)
    if len(text) > max_chars:
        return text[:max_chars] + "\n...(truncated)"
    return text


async def maybe_compact(
    messages: list[dict[str, Any]],
    settings: Settings,
    client: AsyncChatClient,
) -> list[dict[str, Any]]:
    if len(messages) <= settings.session_compact_threshold:
        return messages
    try:
        return await compact_messages(
            messages,
            settings,
            client,
            keep_last=settings.session_compact_keep,
        )
    except Exception:
        return messages
