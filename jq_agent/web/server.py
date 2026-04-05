"""FastAPI：健康检查、单页 UI（Vite 构建产物）、/api/run SSE 流。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Literal

from jq_agent.config import Settings, load_settings
from jq_agent.i18n import UiLang
from jq_agent.orchestration.loop import run_agent_loop

try:
    from fastapi import FastAPI
    from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field
except ImportError as e:
    raise ImportError("Web UI requires: pip install 'jq-agent[web]'") from e

# nginx 等反向代理会缓冲 SSE；显式关闭可减少首包延迟。
SSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

_STATIC_DIR = Path(__file__).resolve().parent / "static"


class RunBody(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=32000)
    max_iter: int | None = Field(None, ge=1, le=64)
    lang: Literal["zh", "en"] = "zh"


def _apply_run_overrides(settings: Settings, body: RunBody) -> Settings:
    if body.max_iter is None:
        return settings
    return settings.model_copy(update={"max_iterations": body.max_iter})


def _static_ready() -> bool:
    return (_STATIC_DIR / "index.html").is_file() and (_STATIC_DIR / "assets").is_dir()


_BUILD_WEB_CMD = "cd jq_agent/web/frontend && npm ci && npm run build"
_FALLBACK_HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/><title>jq-agent Web</title></head>
<body style="font-family:system-ui;padding:2rem;background:#0f172a;color:#e2e8f0;">
<p>Web UI 未构建。请在仓库内执行：</p>
<pre style="background:#1e293b;padding:1rem;border-radius:8px;">{_BUILD_WEB_CMD}</pre>
<p>然后重启 <code>jq-agent web</code>。</p>
</body></html>"""


def create_app() -> FastAPI:
    app = FastAPI(title="jq-agent", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    if _static_ready():
        app.mount(
            "/assets",
            StaticFiles(directory=_STATIC_DIR / "assets"),
            name="assets",
        )

        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(_STATIC_DIR / "index.html")
    else:

        @app.get("/", response_class=HTMLResponse)
        def index_missing_build() -> str:
            return _FALLBACK_HTML

    @app.post("/api/run")
    async def api_run(body: RunBody) -> StreamingResponse:
        settings = _apply_run_overrides(load_settings(), body)
        ui_lang: UiLang = body.lang

        async def event_stream() -> Any:
            queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

            def log_cb(text: str) -> None:
                queue.put_nowait({"event": "log", "text": text})

            async def runner() -> None:
                try:
                    result = await run_agent_loop(
                        body.prompt,
                        settings,
                        ui_lang=ui_lang,
                        log_callback=log_cb,
                    )
                    usage_sum = 0
                    for u in result.usage_records:
                        t = u.get("total_tokens")
                        if isinstance(t, int):
                            usage_sum += t
                    await queue.put(
                        {
                            "event": "done",
                            "stopped_reason": result.stopped_reason,
                            "iterations": result.iterations,
                            "usage_total_tokens": usage_sum,
                        }
                    )
                except Exception as e:
                    await queue.put({"event": "error", "detail": str(e)})
                finally:
                    await queue.put(None)

            task = asyncio.create_task(runner())
            try:
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            finally:
                if not task.done():
                    task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream; charset=utf-8",
            headers=SSE_HEADERS,
        )

    return app


app = create_app()
