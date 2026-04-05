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

type TaskMode = "auto" | "jq_sdk" | "general";

export default function App() {
  const [prompt, setPrompt] = useState("");
  /** server = 不传 task_mode，由服务端 JQ_AGENT_TASK_MODE / .env 决定 */
  const [taskMode, setTaskMode] = useState<"server" | TaskMode>("server");
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
        body: JSON.stringify({
          prompt: p,
          lang: "zh",
          ...(taskMode !== "server" ? { task_mode: taskMode } : {}),
        }),
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
  }, [appendLog, flushNow, prompt, taskMode]);

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
    <div className="bg-moon-stage relative min-h-screen">
      <div
        className="pointer-events-none fixed inset-0 bg-raked opacity-[0.85]"
        aria-hidden
      />
      <div className="relative z-10 mx-auto max-w-3xl px-4 py-10 md:px-6 md:py-14">
        <header className="flex flex-col gap-3 border-b border-[rgba(255,250,230,0.08)] pb-8 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="font-[family-name:var(--font-ui)] text-[0.65rem] font-medium uppercase tracking-[0.35em] text-[var(--color-gold)]">
              JoinQuant · Agent
            </p>
            <h1 className="font-[family-name:var(--font-display)] mt-2 text-2xl font-semibold tracking-[0.02em] text-[var(--color-gofun)] md:text-3xl">
              jq-agent
            </h1>
            <p className="font-[family-name:var(--font-ui)] mt-2 max-w-md text-sm leading-relaxed text-[var(--color-gofun-muted)]">
              聚宽生态编排 · 流式日志与 Pretext 排版。请在运行目录配置{" "}
              <code className="rounded border border-[var(--color-gold-dim)] bg-[rgba(0,0,0,0.25)] px-1.5 py-0.5 font-mono text-xs text-[var(--color-gofun)]">
                JQ_LLM_API_KEY
              </code>
              。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <a
              className="font-[family-name:var(--font-ui)] rounded-full border border-[var(--color-gold-dim)] px-3 py-1.5 text-xs text-[var(--color-gofun-muted)] transition-colors duration-500 hover:border-[var(--color-gold)] hover:text-[var(--color-gofun)]"
              href="/health"
            >
              /health
            </a>
            <a
              className="font-[family-name:var(--font-ui)] rounded-full border border-[var(--color-gold-dim)] px-3 py-1.5 text-xs text-[var(--color-gofun-muted)] transition-colors duration-500 hover:border-[var(--color-gold)] hover:text-[var(--color-gofun)]"
              href="https://github.com/chenglou/pretext"
              target="_blank"
              rel="noreferrer"
            >
              Pretext
            </a>
          </div>
        </header>

        <section className="panel-shoji mt-10 rounded-sm p-6 md:p-8">
          <h2 className="font-[family-name:var(--font-display)] text-lg font-medium text-[var(--color-gofun)]">
            任务
          </h2>
          <p className="font-[family-name:var(--font-ui)] mt-1 text-xs text-[var(--color-gofun-muted)]">
            自然语言描述目标；运行后 SSE 流式输出，可随时停止。
          </p>
          <div className="font-[family-name:var(--font-ui)] mt-4 flex flex-wrap items-center gap-2 text-xs text-[var(--color-gofun-muted)]">
            <label htmlFor="task-mode" className="shrink-0">
              任务模式
            </label>
            <select
              id="task-mode"
              value={taskMode}
              onChange={(e) =>
                setTaskMode(e.target.value as "server" | TaskMode)
              }
              disabled={running}
              className="rounded-sm border border-[rgba(255,250,230,0.12)] bg-[rgba(0,0,0,0.35)] px-2 py-1.5 text-[var(--color-gofun)] focus:border-[rgba(90,99,72,0.85)] focus:outline-none"
            >
              <option value="server">跟随服务端（JQ_AGENT_TASK_MODE）</option>
              <option value="auto">auto（关键词进 jqdatasdk 快路径）</option>
              <option value="jq_sdk">jq_sdk（始终快路径）</option>
              <option value="general">general（通用，不加强）</option>
            </select>
          </div>
          <form onSubmit={onSubmit} className="mt-6">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={8}
              placeholder="例如：查文档里 get_price 的用法，并给出一行示例…"
              disabled={running}
              className="font-[family-name:var(--font-ui)] w-full resize-y rounded-sm border border-[rgba(255,250,230,0.1)] bg-[rgba(0,0,0,0.35)] px-4 py-3 text-sm leading-relaxed text-[var(--color-gofun)] placeholder:text-[var(--color-gofun-muted)]/70 focus:border-[rgba(90,99,72,0.85)] focus:outline-none focus:ring-1 focus:ring-[rgba(90,99,72,0.5)]"
            />
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={running}
                className="btn-primary rounded-sm border border-[var(--color-gold-dim)] bg-[rgba(26,24,22,0.9)] px-6 py-2.5 text-sm font-medium text-[var(--color-gofun)] hover:border-[var(--color-gold)] hover:bg-[rgba(35,32,28,0.95)] disabled:cursor-not-allowed disabled:opacity-40"
              >
                运行
              </button>
              <button
                type="button"
                disabled={!running}
                onClick={stop}
                className="btn-ghost rounded-sm border border-[rgba(255,250,230,0.12)] bg-transparent px-5 py-2.5 text-sm font-medium text-[var(--color-gofun-muted)] hover:border-[var(--color-gold-dim)] hover:text-[var(--color-gofun)] disabled:cursor-not-allowed disabled:opacity-30"
              >
                停止
              </button>
              <span className="font-[family-name:var(--font-ui)] text-xs text-[var(--color-gofun-muted)] md:ml-2">
                {status}
              </span>
            </div>
          </form>
        </section>

        <section className="mt-8">
          <div className="mb-3 flex items-baseline justify-between gap-4">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-medium text-[var(--color-gofun)]">
              输出
            </h2>
            <span className="font-[family-name:var(--font-ui)] text-[0.65rem] uppercase tracking-[0.2em] text-[var(--color-gold)]/80">
              SSE · Virtual
            </span>
          </div>
          <LogView text={logText} />
        </section>

        <footer className="font-[family-name:var(--font-ui)] mt-12 border-t border-[rgba(255,250,230,0.06)] pt-6 text-center text-[0.65rem] leading-relaxed text-[var(--color-gofun-muted)]">
          jq-agent Web · 月夜底色、障子纸玻璃与金褐描边（与 Goshu / Yonderaura 系作品同向的克制东方气质）
        </footer>
      </div>
    </div>
  );
}
