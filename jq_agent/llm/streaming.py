"""OpenAI 兼容 SSE 流式 chat/completions — asyncio + AsyncChatClient。"""

from __future__ import annotations

import json
from typing import Any

from jq_agent.llm.client import AsyncChatClient


async def stream_complete_async(
    client: AsyncChatClient,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    tool_choice: str | None,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    body: dict[str, Any] = {
        "model": client.settings.model,
        "messages": messages,
    }
    if tools:
        body["tools"] = tools
        if tool_choice is not None:
            body["tool_choice"] = tool_choice

    text_printed = ""
    usage: dict[str, Any] = {}
    content_buf: list[str] = []
    tc_parts: dict[int, dict[str, Any]] = {}

    async with client.stream_request(body) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="replace")
            if not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            u = chunk.get("usage")
            if isinstance(u, dict):
                usage.update(u)
            ch0 = (chunk.get("choices") or [{}])[0]
            delta = ch0.get("delta") or {}
            if delta.get("content"):
                piece = delta["content"]
                content_buf.append(piece)
                text_printed += piece
            for tc in delta.get("tool_calls") or []:
                idx = int(tc.get("index", 0))
                slot = tc_parts.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                if tc.get("id"):
                    slot["id"] = tc["id"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    slot["name"] = fn["name"]
                if fn.get("arguments"):
                    slot["arguments"] += fn.get("arguments", "")

    message: dict[str, Any] = {"role": "assistant", "content": "".join(content_buf) or None}
    if tc_parts:
        tool_calls = []
        for idx in sorted(tc_parts.keys()):
            slot = tc_parts[idx]
            tool_calls.append(
                {
                    "id": slot.get("id") or f"call_{idx}",
                    "type": "function",
                    "function": {
                        "name": slot.get("name", ""),
                        "arguments": slot.get("arguments", ""),
                    },
                }
            )
        message["tool_calls"] = tool_calls

    fake: dict[str, Any] = {"choices": [{"message": message, "finish_reason": "stop"}]}
    if usage:
        fake["usage"] = usage
    return fake, text_printed, usage
