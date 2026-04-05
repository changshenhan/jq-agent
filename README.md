<div align="center">

# jq-agent

**Open-source JoinQuant-style quant Agent framework** — orchestration loop · doc retrieval (keyword + optional API embeddings) · sandboxed tools · optional Web UI.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://github.com/changshenhan/jq-agent)
[![License: MIT](https://img.shields.io/badge/license-MIT-5c6bc0?style=flat)](LICENSE)

[中文文档](README.zh-CN.md) · [Architecture](#architecture) · [Comparison](#comparison-claw-code-kilo-code-and-jq-agent) · [CLI](#cli--language) · [Tutorial](#integrated-tutorial-bilingual)

</div>

---

## What this project does

**English.** jq-agent is an **open-source orchestration framework** for building **JoinQuant / jqdatasdk–aware quant agents**. It runs a **tool-calling loop** (plan → execute → observe) over a **sandboxed workspace** (under `.jq-agent/`), so the model can look up API snippets, write strategy files, lint them, run backtests in a subprocess, and parse metrics—instead of only chatting. Document retrieval combines **bundled keyword snippets**, optional **user-built slices** from the official GitHub repo, and—when you configure a provider key—**semantic hits** via the provider’s **Embeddings HTTP API**. The CLI is **bilingual (zh/en)**; sessions can be persisted (JSON or SQLite); **MCP stdio** can expose core tools to editors; an optional **FastAPI + SSE** browser UI is available. **It is not** a hosted product or a broker: you bring your own **LLM API** and (for live jqdatasdk) your own **JoinQuant credentials** via environment or `.env` (never commit secrets).

**中文。** jq-agent 是面向 **聚宽 / jqdatasdk** 的**开源 Agent 编排框架**：在 **`.jq-agent/` 沙箱**内完成 **规划 → 执行 → 观察**，支持查文档、写策略、ruff、子进程回测与指标解析；检索融合**关键词**、可选 **GitHub 官方切片**与 **Embeddings API** 语义命中；CLI **中英**；会话可落盘；可选 **浏览器界面（SSE 日志）**。**非**托管产品：需自行配置大模型与聚宽相关环境变量。

---

## Why jq-agent?

| Ordinary chat | jq-agent |
|-----------------|----------|
| Returns prose only | **Plan → Execute → Observe** with **tool calls** |
| Hallucinated APIs | **`query_jq_docs`** against **keyword + optional Embeddings** |
| Unsafe writes | Files & backtests confined to a **sandbox** |

---

## Features

- **Agentic loop** — OpenAI-compatible **function calling** until done or **max iterations**.
- **Tools** — `query_jq_docs`, `read_file`, `write_strategy_file`, `execute_backtest`, `analyze_backtest_metrics`, `lint_strategy_file` (ruff), `research_subtask`.
- **Path policy** — paths under workspace **`.jq-agent/`**; optional **`JQ_PERMISSION_MODE=strict`** → writes only **`scratchpad/`**.
- **Sessions** — `jq-agent run --session NAME` / `--resume`; SQLite or JSON backend; **`fork_subagent_session`**; **`jq-agent session tree`**.
- **Streaming** — `jq-agent run --stream` or **`JQ_LLM_STREAM=true`** (SSE).
- **Parallel tools** — **`asyncio.gather`** + **`asyncio.to_thread`** for concurrent tool calls.
- **Compaction** — long histories summarized via LLM (**`JQ_SESSION_COMPACT_*`**).
- **MCP** — **`jq-agent mcp-stdio`** (`pip install 'jq-agent[mcp]'`).
- **Usage log** — optional **`~/.jq-agent/usage.jsonl`**.
- **JSON repair** — malformed tool arguments retried with heuristics.
- **Bilingual CLI** — **`--lang`**, **`JQ_LANG`**, **`jq-agent config lang`**.
- **Terminal UX** — **Rich** panel (goal / steps / tokens), **spinner** for **`execute_backtest`**, colored table for **`analyze_backtest_metrics`**.
- **Equity HTML** — strategy writes **`scratchpad/backtest_equity.csv`** → auto **`scratchpad/backtest_result.html`** (Plotly).
- **Web UI (optional)** — **`pip install 'jq-agent[web]'`** → **`jq-agent web`** → **`/`** + **`/api/run`** SSE (`log` / `done` / `error`).

---

## Project status

| Area | Status |
|------|--------|
| Orchestration, sandbox, tools, sessions, MCP, strict mode, compaction | **Done** |
| Doc retrieval (keyword + slices + Embeddings API) | **Done** |
| CLI visualization + backtest metrics table + Plotly equity chart | **Done** |
| FastAPI + SSE Web UI (`[web]`) | **Done** |
| Full SaaS, broker adapters, bundled local embedding models | **Roadmap** — see below |

---

## Comparison: claw-code, Kilo Code, and jq-agent

This section answers the “study **claw-code** vs **Kilo Code**, compare pros/cons” style assignment: it is based on **public repositories and docs** only (no reliance on proprietary leaks as a source of truth). In this workspace, **claw-code** refers to the open **claw-code** rewrite project (e.g. [instructkr/claw-code](https://github.com/instructkr/claw-code)–style harness: Python + Rust ports, MCP, compaction). **Kilo Code** refers to the open **[kilo-org/kilocode](https://github.com/kilo-org/kilocode)** stack and [kilo.ai docs](https://kilo.ai/docs/).

| Dimension | **claw-code** (harness rewrite) | **Kilo Code** | **jq-agent** (this repo) |
|-----------|-----------------------------------|---------------|---------------------------|
| **Primary goal** | Rebuild a **general agent harness** (tools, session, MCP, CLI) inspired by well-known harness patterns; Rust/Python runtime | **IDE-integrated coding agent**: central CLI + HTTP/SSE, many models, LSP, tools, cloud option | **Quant / JoinQuant domain agent**: jqdatasdk docs, **sandboxed** strategy files, **subprocess backtests**, metrics & plots |
| **Surface** | CLI / runtime ports, plugin-style tools | VS Code / JetBrains / TUI / HTTP API | **Thin CLI** + optional **FastAPI Web UI** + **MCP stdio** |
| **Context & memory** | Session state, **compaction**, MCP orchestration (as in upstream harness design) | Session manager, checkpoints, multi-mode (architect/coder/…) | **Session** JSON/SQLite, **LLM compaction**, retrieval injected into **system** |
| **Strengths** | Deep **harness engineering** narrative; tool/MCP story; performance path (Rust) | **Mature product shape**: provider router, LSP, marketplace, multi-client | **Domain fit**: `query_jq_docs` + index slices + **execute_backtest** + **equity HTML**; minimal moving parts in **Python** |
| **Trade-offs** | Heavy scope; not JoinQuant-specific | Larger install & ops; not specialized for **jqdatasdk** or broker rules | **Narrow**: not a full IDE agent; embeddings via **HTTP API** only (no bundled local embed model yet) |

**Why jq-agent still matters next to them:** claw-code and Kilo Code optimize for **general software engineering** agents. jq-agent **intentionally** narrows the tool contract to **JoinQuant-style workflows** (docs → strategy → lint → backtest → metrics), which is what a quant stack audit cares about. Ideas cross-pollinate (sandbox, compaction, MCP, JSON repair), but **jq-agent is not a fork** of either codebase.

**中文摘要：** 上表从**公开仓库**对比了本机参考的 **claw-code** 系 harness 重写与 **Kilo Code** 通用编程 Agent；**jq-agent** 选择做**聚宽/jqdatasdk 垂直闭环**（检索、沙箱、回测、指标与可视化），而非复刻 IDE 级全家桶——这与“学习 harness、再对比取舍”的任务一致，且边界清晰。

---

## Security & credentials

- **Never commit** API keys, passwords, or phone numbers. Use **`.env`** (listed in **`.gitignore`**) or shell exports; start from **`.env.example`** only as a template.
- Configure **`JQ_LLM_API_KEY`** (or legacy **`JQ_OPENAI_API_KEY`**) for OpenAI-compatible Chat + Embeddings. JoinQuant / **`jqdatasdk`** credentials belong in **your** environment when you run strategies—**not** in the repository.

---

## Architecture

```mermaid
flowchart LR
  subgraph orch [Orchestration]
    LLM[LLM API]
    Loop[Plan / Execute / Observe]
  end
  subgraph data [Knowledge]
    Idx[Keyword + optional API embeddings]
  end
  subgraph tools [Tools]
    Q[query_jq_docs]
    W[write_strategy_file]
    X[execute_backtest]
  end
  User([User]) --> Loop
  Loop --> LLM
  LLM --> Q
  Q --> Idx
  LLM --> W
  LLM --> X
  X -->|stdout / stderr| Loop
```

---

## Quick start

```bash
git clone https://github.com/changshenhan/jq-agent.git
cd jq-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
pip install -e ".[web]"    # optional: jq-agent web
cp .env.example .env       # edit locally; do not commit
```

Configuration is read from the **current working directory** (`.env` or environment variables).

### Doc index (official jqdatasdk → JSON; optional Embeddings)

Sources: [**JoinQuant/jqdatasdk**](https://github.com/JoinQuant/jqdatasdk) → slices → **`~/.jq-agent/jqdatasdk_index/chunks.json`**. With a provider key, **`jq-agent index build`** can call **`/v1/embeddings`** for semantic **`query_jq_docs`**.

```bash
jq-agent index build
jq-agent index status
# jq-agent index build --full   # large: alpha101 / alpha191 / technical_analysis
```

### Environment variables (reference)

| Variable | Role |
|----------|------|
| `JQ_LLM_API_KEY` | Chat + embeddings (legacy: `JQ_OPENAI_API_KEY`) |
| `JQ_LLM_BASE_URL` | Default `https://api.openai.com/v1` |
| `JQ_EMBEDDING_MODEL` | Embeddings model id |
| `JQ_MODEL` | Chat model id |
| `JQ_MAX_ITERATIONS` | Loop cap (default `16`) |
| `JQ_LANG` | CLI UI: `zh` or `en` |
| `JQ_BACKTEST_TIMEOUT_SEC` | Subprocess timeout for **`execute_backtest`** |
| `JQ_LLM_STREAM` | SSE streaming for chat |
| `JQ_PERMISSION_MODE` | `normal` or `strict` (writes → `scratchpad/` only) |
| `JQ_USAGE_LOG` | Append usage to `~/.jq-agent/usage.jsonl` |
| `JQ_SESSION_BACKEND` | `sqlite` or `json` |
| `JQ_SESSION_COMPACT_THRESHOLD` / `JQ_SESSION_COMPACT_KEEP` | Session compaction |
| `JQ_PHONE` / `JQ_PASSWORD` | JoinQuant / **`jqdatasdk`** when running real backtests |

See **`.env.example`** for the full list and comments.

### Run

```bash
jq-agent doctor
jq-agent run "Look up get_price in the docs and summarize in one sentence."
```

**DeepSeek (example)**

```bash
export JQ_LLM_BASE_URL=https://api.deepseek.com/v1
export JQ_MODEL=deepseek-chat
jq-agent run "Query docs for 沪深300 index symbol"
```

Set secrets via **`export`** or entries in **`.env`** (not committed).

---

## CLI & language

| Command | Purpose |
|---------|---------|
| `jq-agent doctor` | Sandbox path, key presence, model, doc index status |
| `jq-agent run "..."` | Agent loop |
| `jq-agent run --session NAME --resume` | Continue session |
| `jq-agent run --stream` | SSE streaming |
| `jq-agent config lang` / `config show` | UI language (persisted) |
| `jq-agent index build` / `index status` | Doc slices + optional embeddings |
| `jq-agent session list` / `path` / `tree` | Sessions |
| `jq-agent mcp-stdio` | MCP (`pip install 'jq-agent[mcp]'`) |
| `jq-agent web` | Browser UI (`pip install 'jq-agent[web]'`) |

Priority: **`--lang` > `JQ_LANG` > saved config > `zh`**.

---

## Roadmap · next step

Pluggable **local / self-hosted embedding** backends (explicit opt-in) for deployments that cannot use cloud Embeddings—without binding a single vendor. Chat and embeddings today are **HTTP APIs** only.

---

## Integrated tutorial (bilingual)

Copy-paste paths may differ on your OS.

### English

1. Clone & install — see [Quick start](#quick-start). Optional: **`pip install 'jq-agent[mcp]'`** or **`'jq-agent[web]'`**.
2. Copy **`.env.example`** → **`.env`** and fill keys **locally** (never commit).
3. **`jq-agent doctor`** — verify sandbox, keys, index.
4. **`jq-agent index build`** (optional) — **`index status`** for metadata.
5. **`jq-agent config lang en`** if you want English CLI labels.
6. **`jq-agent run "…"`** — try a doc query; use **`--session`** / **`--resume`** for multi-turn.
7. For **live jqdatasdk** backtests, set account-related vars per JoinQuant docs; copy **`examples/real_price_smoke.py`** into **`scratchpad/`** and call **`execute_backtest`** from the agent (`pip install jqdatasdk`).
8. **`JQ_PERMISSION_MODE=strict`** — restrict writes to **`scratchpad/`**.
9. **`jq-agent mcp-stdio`** — wire MCP hosts (e.g. Cursor).

### 中文

1. 克隆与安装见 [Quick start](#quick-start)；可选安装 **`[mcp]`**、**`[web]`**。
2. 复制 **`.env.example`** 为 **`.env`**，仅在本地填写密钥（**勿提交**）。
3. **`jq-agent doctor`** 检查环境与索引。
4. **`jq-agent index build`** / **`index status`**（可选）。
5. **`jq-agent config lang zh`** 等设置界面语言。
6. **`jq-agent run "…"`** 试跑；需要时用 **`--session`** / **`--resume`**。
7. 真实行情回测：按聚宽要求配置账号相关变量；可将 **`examples/real_price_smoke.py`** 放入 **`scratchpad/`** 并通过工具执行（需 **`jqdatasdk`**）。
8. **`JQ_PERMISSION_MODE=strict`** 限制仅写入 **`scratchpad/`**。
9. **`jq-agent mcp-stdio`** 接入 MCP 宿主。

---

## Disclaimer

For **research and education** only. **Not** investment advice. You are responsible for compliance with exchanges and data licenses.

---

## License

MIT — see [LICENSE](LICENSE).
