"""FastAPI：健康检查、单页 UI、/api/run SSE 流。"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

from jq_agent.config import Settings, load_settings
from jq_agent.i18n import UiLang
from jq_agent.orchestration.loop import run_agent_loop

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, StreamingResponse
    from pydantic import BaseModel, Field
except ImportError as e:
    raise ImportError("Web UI requires: pip install 'jq-agent[web]'") from e


class RunBody(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=32000)
    max_iter: int | None = Field(None, ge=1, le=64)
    lang: Literal["zh", "en"] = "zh"


def _apply_run_overrides(settings: Settings, body: RunBody) -> Settings:
    if body.max_iter is None:
        return settings
    return settings.model_copy(update={"max_iterations": body.max_iter})


INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>jq-agent Web</title>
  <style>
    :root { font-family: system-ui, sans-serif; background: #0f1419; color: #e6edf3; }
    body { max-width: 56rem; margin: 2rem auto; padding: 0 1rem; }
    h1 { font-weight: 600; font-size: 1.25rem; }
    textarea { width: 100%; min-height: 8rem; padding: 0.75rem; border-radius: 8px;
      border: 1px solid #30363d; background: #161b22; color: inherit; box-sizing: border-box; }
    button { margin-top: 0.75rem; padding: 0.5rem 1rem; border-radius: 8px; border: none;
      background: #238636; color: #fff; cursor: pointer; font-weight: 500; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    pre#log { margin-top: 1rem; padding: 1rem; border-radius: 8px; background: #161b22;
      border: 1px solid #30363d; white-space: pre-wrap; word-break: break-word; min-height: 4rem;
      font-size: 0.85rem; line-height: 1.45; }
    .meta { font-size: 0.8rem; color: #8b949e; margin-top: 0.5rem; }
    a { color: #58a6ff; }
  </style>
</head>
<body>
  <h1>jq-agent · Web</h1>
  <p class="meta">需要配置 <code>JQ_LLM_API_KEY</code>；输出为 SSE 流式日志。<a href="/health">/health</a></p>
  <textarea id="prompt" placeholder="输入任务，例如：查文档里 get_price 的用法…"></textarea>
  <div>
    <button type="button" id="run">运行</button>
    <span class="meta" id="status"></span>
  </div>
  <pre id="log"></pre>
  <script>
    const logEl = document.getElementById('log');
    const statusEl = document.getElementById('status');
    const btn = document.getElementById('run');
    document.getElementById('run').onclick = async () => {
      const prompt = document.getElementById('prompt').value.trim();
      if (!prompt) { statusEl.textContent = '请输入内容'; return; }
      btn.disabled = true;
      logEl.textContent = '';
      statusEl.textContent = '运行中…';
      try {
        const res = await fetch('/api/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, lang: 'zh' }),
        });
        if (!res.ok) { statusEl.textContent = 'HTTP ' + res.status; btn.disabled = false; return; }
        const reader = res.body.getReader();
        const dec = new TextDecoder();
        let buf = '';
        const NL = String.fromCharCode(10);
        const sep = NL + NL;
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          let idx;
          while ((idx = buf.indexOf(sep)) >= 0) {
            const chunk = buf.slice(0, idx);
            buf = buf.slice(idx + sep.length);
            const line = chunk.split(NL).find(l => l.startsWith('data: '));
            if (!line) continue;
            let ev;
            try { ev = JSON.parse(line.slice(6)); } catch (e) { continue; }
            if (ev.event === 'log' && ev.text) logEl.textContent += ev.text;
            if (ev.event === 'done') {
              statusEl.textContent = '结束: ' + (ev.stopped_reason || '') + ' · 轮次 ' + (ev.iterations ?? '');
            }
            if (ev.event === 'error') {
              statusEl.textContent = '错误: ' + (ev.detail || '');
              logEl.textContent += NL + '[error] ' + (ev.detail || '') + NL;
            }
          }
        }
      } catch (e) {
        statusEl.textContent = String(e);
      }
      btn.disabled = false;
    };
  </script>
</body>
</html>"""


def create_app() -> FastAPI:
    app = FastAPI(title="jq-agent", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML

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
                await task

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return app


app = create_app()
