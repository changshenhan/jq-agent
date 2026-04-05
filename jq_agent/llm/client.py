from __future__ import annotations

from typing import Any

import httpx

from jq_agent.config import Settings
from jq_agent.llm.transport import (
    build_httpx_limits,
    build_httpx_timeout,
    use_http2,
)


class AsyncChatClient:
    """OpenAI 兼容 Chat Completions — asyncio + httpx.AsyncClient（连接池 / 可选 HTTP/2）。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._url = settings.llm_base_url.rstrip("/") + "/chat/completions"
        self._client = httpx.AsyncClient(
            timeout=build_httpx_timeout(settings),
            limits=build_httpx_limits(settings),
            http2=use_http2(settings),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = "auto",
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
        }
        if tools:
            body["tools"] = tools
            if tool_choice is not None:
                body["tool_choice"] = tool_choice

        r = await self._client.post(self._url, headers=headers, json=body)
        r.raise_for_status()
        return r.json()

    def stream_request(self, body: dict[str, Any]) -> Any:
        """返回 httpx 异步流上下文管理器（async with）。"""
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        body = {**body, "stream": True}
        return self._client.stream("POST", self._url, headers=headers, json=body)
