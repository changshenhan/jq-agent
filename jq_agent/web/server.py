"""FastAPI：健康检查、单页 UI、/api/run SSE 流。

SSE 对齐常见生产实践：代理可关缓冲、禁用缓存变形；客户端用 rAF 批量写 DOM（见 INDEX_HTML）。
"""

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

# nginx 等反向代理会缓冲 SSE；显式关闭可减少首包延迟。
SSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class RunBody(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=32000)
    max_iter: int | None = Field(None, ge=1, le=64)
    lang: Literal["zh", "en"] = "zh"


def _apply_run_overrides(settings: Settings, body: RunBody) -> Settings:
    if body.max_iter is None:
        return settings
    return settings.model_copy(update={"max_iterations": body.max_iter})


# Tailwind Play CDN + Fetch Streams + rAF 批量 DOM（主流低延迟前端模式，无需打包）。
INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN" class="h-full">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>jq-agent Web</title>
  <link rel="dns-prefetch" href="https://cdn.tailwindcss.com"/>
  <link rel="preconnect" href="https://cdn.tailwindcss.com" crossorigin/>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-full bg-slate-950 text-slate-100 antialiased">
  <div class="mx-auto max-w-3xl px-4 py-8">
    <h1 class="text-xl font-semibold tracking-tight text-white">jq-agent · Web</h1>
    <p class="mt-2 text-sm text-slate-400">
      需要配置
      <code class="rounded bg-slate-800 px-1 py-0.5 text-slate-200">JQ_LLM_API_KEY</code>
      ；输出为 SSE 流式日志（Fetch Streams + requestAnimationFrame 批量刷新）。
      <a class="text-sky-400 hover:underline" href="/health">/health</a>
    </p>
    <textarea id="prompt" rows="8" placeholder="输入任务，例如：查文档里 get_price 的用法…"
      class="mt-4 w-full resize-y rounded-lg border border-slate-700 bg-slate-900 px-3 py-2
        text-sm text-slate-100 placeholder:text-slate-500
        focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"></textarea>
    <div class="mt-3 flex flex-wrap items-center gap-3">
      <button type="button" id="run" class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium
        text-white shadow hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50">运行</button>
      <button type="button" id="stop" disabled class="rounded-lg border border-slate-600 bg-slate-800 px-4 py-2
        text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed
        disabled:opacity-40">停止</button>
      <span class="text-sm text-slate-400" id="status"></span>
    </div>
    <div id="log-wrap" class="mt-4 max-h-[min(60vh,28rem)] overflow-y-auto overflow-x-hidden rounded-lg
      border border-slate-700 bg-slate-900 contain-content [scrollbar-gutter:stable]">
      <pre id="log" class="min-h-16 whitespace-pre-wrap break-words p-4 text-[0.85rem] leading-relaxed
        text-slate-200"></pre>
    </div>
  </div>
  <script>
(function () {
  const logEl = document.getElementById('log');
  const logWrap = document.getElementById('log-wrap');
  const statusEl = document.getElementById('status');
  const runBtn = document.getElementById('run');
  const stopBtn = document.getElementById('stop');
  const NL = String.fromCharCode(10);
  const sep = NL + NL;
  let pending = '';
  let rafId = 0;
  let ac = null;
  function flushNow() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    }
    if (pending) {
      logEl.textContent += pending;
      pending = '';
      logWrap.scrollTop = logWrap.scrollHeight;
    }
  }
  function appendLog(s) {
    pending += s;
    if (!rafId) {
      rafId = requestAnimationFrame(function () {
        rafId = 0;
        if (pending) {
          logEl.textContent += pending;
          pending = '';
          logWrap.scrollTop = logWrap.scrollHeight;
        }
      });
    }
  }
  runBtn.addEventListener('click', async function () {
    const prompt = document.getElementById('prompt').value.trim();
    if (!prompt) {
      statusEl.textContent = '请输入内容';
      return;
    }
    ac = new AbortController();
    runBtn.disabled = true;
    stopBtn.disabled = false;
    logEl.textContent = '';
    statusEl.textContent = '运行中…';
    try {
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt, lang: 'zh' }),
        signal: ac.signal,
        cache: 'no-store',
      });
      if (!res.ok) {
        statusEl.textContent = 'HTTP ' + res.status;
        return;
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      while (true) {
        const step = await reader.read();
        if (step.done) break;
        buf += dec.decode(step.value, { stream: true });
        let idx;
        while ((idx = buf.indexOf(sep)) >= 0) {
          const chunk = buf.slice(0, idx);
          buf = buf.slice(idx + sep.length);
          const line = chunk.split(NL).find(function (l) { return l.startsWith('data: '); });
          if (!line) continue;
          let ev;
          try {
            ev = JSON.parse(line.slice(6));
          } catch (e) {
            continue;
          }
          if (ev.event === 'log' && ev.text) appendLog(ev.text);
          if (ev.event === 'done') {
            statusEl.textContent =
              '结束: ' + (ev.stopped_reason || '') + ' · 轮次 ' + (ev.iterations ?? '');
          }
          if (ev.event === 'error') {
            statusEl.textContent = '错误: ' + (ev.detail || '');
            appendLog(NL + '[error] ' + (ev.detail || '') + NL);
          }
        }
      }
    } catch (e) {
      if (e && e.name === 'AbortError') {
        statusEl.textContent = '已停止';
      } else {
        statusEl.textContent = String(e);
      }
    } finally {
      flushNow();
      runBtn.disabled = false;
      stopBtn.disabled = true;
      ac = null;
    }
  });
  stopBtn.addEventListener('click', function () {
    if (ac) ac.abort();
  });
})();
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
