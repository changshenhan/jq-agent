import {
  useCallback,
  useEffect,
  useRef,
  useState,
  startTransition,
  type FormEvent,
} from "react";
import { LogView } from "./LogView";

const NL = "\n";
const SSE_SEP = "\n\n";

type SseEvent =
  | { event: "log"; text: string }
  | { event: "done"; stopped_reason?: string; iterations?: number }
  | { event: "error"; detail?: string };

function parseSseBlocks(buffer: string): { rest: string; events: SseEvent[] } {
  const events: SseEvent[] = [];
  let rest = buffer;
  let idx: number;
  while ((idx = rest.indexOf(SSE_SEP)) >= 0) {
    const chunk = rest.slice(0, idx);
    rest = rest.slice(idx + SSE_SEP.length);
    const line = chunk.split(NL).find((l) => l.startsWith("data: "));
    if (!line) continue;
    try {
      events.push(JSON.parse(line.slice(6)) as SseEvent);
    } catch {
      /* skip malformed */
    }
  }
  return { rest, events };
}

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState("");
  const [running, setRunning] = useState(false);
  const [logText, setLogText] = useState("");

  const logTextRef = useRef("");
  const pendingRef = useRef("");
  const rafRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const flushNow = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
    if (pendingRef.current) {
      logTextRef.current += pendingRef.current;
      pendingRef.current = "";
      setLogText(logTextRef.current);
    }
  }, []);

  const appendLog = useCallback((s: string) => {
    pendingRef.current += s;
    if (!rafRef.current) {
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = 0;
        if (pendingRef.current) {
          logTextRef.current += pendingRef.current;
          pendingRef.current = "";
          setLogText(logTextRef.current);
        }
      });
    }
  }, []);

  const run = useCallback(async () => {
    const p = prompt.trim();
    if (!p) {
      startTransition(() => setStatus("请输入内容"));
      return;
    }

    abortRef.current = new AbortController();
    const ac = abortRef.current;
    setRunning(true);
    startTransition(() => {
      setStatus("运行中…");
    });
    logTextRef.current = "";
    pendingRef.current = "";
    setLogText("");

    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: p, lang: "zh" }),
        signal: ac.signal,
        cache: "no-store",
      });

      if (!res.ok) {
        startTransition(() => setStatus(`HTTP ${res.status}`));
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        startTransition(() => setStatus("无响应体"));
        return;
      }

      const dec = new TextDecoder();
      let buf = "";

      for (;;) {
        const step = await reader.read();
        if (step.done) break;
        buf += dec.decode(step.value, { stream: true });
        const parsed = parseSseBlocks(buf);
        buf = parsed.rest;
        for (const ev of parsed.events) {
          if (ev.event === "log" && ev.text) appendLog(ev.text);
          if (ev.event === "done") {
            startTransition(() =>
              setStatus(
                `结束: ${ev.stopped_reason ?? ""} · 轮次 ${ev.iterations ?? ""}`,
              ),
            );
          }
          if (ev.event === "error") {
            startTransition(() => setStatus(`错误: ${ev.detail ?? ""}`));
            appendLog(`${NL}[error] ${ev.detail ?? ""}${NL}`);
          }
        }
      }
    } catch (e: unknown) {
      const err = e as { name?: string };
      if (err?.name === "AbortError") {
        startTransition(() => setStatus("已停止"));
      } else {
        startTransition(() => setStatus(String(e)));
      }
    } finally {
      flushNow();
      setRunning(false);
      abortRef.current = null;
    }
  }, [appendLog, flushNow, prompt]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      abortRef.current?.abort();
    };
  }, []);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void run();
  }

  return (
    <div className="min-h-full bg-slate-950 text-slate-100 antialiased">
      <div className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="text-xl font-semibold tracking-tight text-white">
          jq-agent · Web
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          需要配置{" "}
          <code className="rounded bg-slate-800 px-1 py-0.5 text-slate-200">
            JQ_LLM_API_KEY
          </code>
          ；日志排版{" "}
          <a
            className="text-sky-400 hover:underline"
            href="https://github.com/chenglou/pretext"
            target="_blank"
            rel="noreferrer"
          >
            @chenglou/pretext
          </a>{" "}
          + 虚拟列表，SSE 仍按帧合并写入。
          <a className="ml-1 text-sky-400 hover:underline" href="/health">
            /health
          </a>
        </p>

        <form onSubmit={onSubmit} className="mt-4">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={8}
            placeholder="输入任务，例如：查文档里 get_price 的用法…"
            className="w-full resize-y rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            disabled={running}
          />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={running}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              运行
            </button>
            <button
              type="button"
              disabled={!running}
              onClick={stop}
              className="rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              停止
            </button>
            <span className="text-sm text-slate-400">{status}</span>
          </div>
        </form>

        <div className="mt-4">
          <LogView text={logText} />
        </div>
      </div>
    </div>
  );
}
