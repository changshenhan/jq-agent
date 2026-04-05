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


# Tailwind CSS Play CDN — utility-first styling aligned with common 2024+ web tooling (no bundler).
INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN" class="h-full">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>jq-agent Web</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-full bg-slate-950 text-slate-100 antialiased">
  <div class="mx-auto max-w-3xl px-4 py-8">
    <h1 class="text-xl font-semibold tracking-tight text-white">jq-agent · Web</h1>
    <p class="mt-2 text-sm text-slate-400">
      需要配置
      <code class="rounded bg-slate-800 px-1 py-0.5 text-slate-200">JQ_LLM_API_KEY</code>
      ；输出为 SSE 流式日志。
      <a class="text-sky-400 hover:underline" href="/health">/health</a>
    </p>
    <textarea id="prompt" rows="8" placeholder="输入任务，例如：查文档里 get_price 的用法…"
      class="mt-4 w-full resize-y rounded-lg border border-slate-700 bg-slate-900 px-3 py-2
        text-sm text-slate-100 placeholder:text-slate-500
        focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"></textarea>
    <div class="mt-3 flex flex-wrap items-center gap-3">
      <button type="button" id="run" class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium
        text-white shadow hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50">运行</button>
      <span class="text-sm text-slate-400" id="status"></span>
    </div>
    <pre id="log" class="mt-4 min-h-16 whitespace-pre-wrap break-words rounded-lg border
      border-slate-700 bg-slate-900 p-4 text-[0.85rem] leading-relaxed text-slate-200"></pre>
  </div>
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
