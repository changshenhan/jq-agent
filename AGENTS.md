# AGENTS.md — 供 AI Agent / 宿主 阅读的协作说明

> 若你在 **Cursor、Claude Code、Kilocode、MCP 宿主** 等环境中被指派处理本仓库，请先读本文再改代码或给用户提供命令。

## 本项目是什么

- **jq-agent**：面向 **聚宽 / `jqdatasdk`** 的 **Python** 编排框架（Plan → Execute → Observe），工具调用走 **OpenAI 兼容的 function calling**。
- **沙箱根目录**：默认 **`.jq-agent/`**（相对当前工作目录），由 **`JQ_SANDBOX_DIR`** 或配置覆盖。所有读写路径必须落在该根目录下（见 `jq_agent/permissions.py`）。
- **不是**托管产品：需要用户自行配置 **LLM API** 与（若跑真实行情）**聚宽账号**环境变量。

## 你（Agent）应遵守的规则

1. **绝不**在仓库中写入真实密钥、手机号、密码；**`.env` 已 gitignore**，只可参考 **`.env.example`** 的键名。
2. 策略与回测相关文件应放在 **`scratchpad/`** 下（与 system prompt、`.cursorrules` 一致）。
3. 若用户启用 **`JQ_PERMISSION_MODE=strict`**，写入工具仅限 **`scratchpad/`**；**`run_terminal_cmd` 会被禁用**。
4. 修改代码时保持与现有风格一致；**不要**为演示任务随意删除测试或扩大无关重构范围（除非用户要求）。

## 用户常用命令（你可据此建议）

| 场景 | 命令 |
|------|------|
| 环境诊断 | `jq-agent doctor` |
| 跑一轮 Agent | `jq-agent run "自然语言任务"` |
| 文档索引 | `jq-agent index build`（需网络拉取 GitHub；可选 Embeddings） |
| MCP 服务 | `pip install 'jq-agent[mcp]' && jq-agent mcp-stdio` |
| 浏览器 SSE UI | `pip install 'jq-agent[web]' && jq-agent web` → 打开提示的 `http://127.0.0.1:8765/` |

## 工具清单（供你规划调用顺序）

| 工具名 | 用途 |
|--------|------|
| `query_jq_docs` | 检索 jqdatasdk 官方片段（先查再写代码） |
| `read_file` / `write_strategy_file` | 读/写沙箱内文件 |
| `search_replace` | 唯一匹配局部替换（IDE 式） |
| `list_directory` / `glob_files` / `grep_workspace` | 浏览与搜索（IDE Agent 模式，默认开启） |
| `run_terminal_cmd` | 沙箱根目录执行命令（**strict 时禁用**） |
| `lint_strategy_file` | ruff 检查 `.py` |
| `execute_backtest` | 子进程跑策略（需 **`JQ_PHONE` / `JQ_PASSWORD`**） |
| `analyze_backtest_metrics` | 解析指标 JSON / stdout |
| `research_subtask` | 单轮无工具推理 |
| `fork_subagent_session` | 需 CLI `--session` 时会话树分叉 |
| `github_search_repositories` / `github_search_users` | GitHub 公开搜索（REST API） |
| `github_get_user` / `github_get_repository` | 公开用户/仓库元数据（非网页爬取） |

量化推荐闭环：**`query_jq_docs` → 写/改策略 → `lint_strategy_file` → `execute_backtest` → `analyze_backtest_metrics`**；净值图依赖策略写出 **`scratchpad/backtest_equity.csv`**。

## 关键环境变量（名称即可，不要填真值）

- **`JQ_LLM_API_KEY`**：大模型（兼容 `JQ_OPENAI_API_KEY`）。
- **`JQ_LLM_BASE_URL` / `JQ_MODEL`**：底座与模型 id。
- **`JQ_LLM_STREAM`**：流式输出（降低首字延迟，推荐 `true`）。
- **`JQ_LLM_HTTP2` / `JQ_LLM_HTTP_*`**：HTTP/2、连接池与分阶段超时（见 README **Performance**）。
- **`JQ_PHONE` / `JQ_PASSWORD`**：聚宽 / `jqdatasdk`（仅用户本机环境）。
- **`JQ_IDE_AGENT_TOOLS`**：是否注册 IDE 类工具（默认 `true`）。
- **`JQ_GITHUB_TOOLS`** / **`JQ_GITHUB_TOKEN`**（或 **`GITHUB_TOKEN`**）：GitHub 公开 API 工具开关与可选 token（提配额）。
- 完整列表见 **`.env.example`** 与 **[README.md](README.md)** 环境表。

## 可视化栈（改 UI/图表时请对齐）

- **图表**：**Plotly.py 6.x**（交互 HTML，与 `jq_agent/tools/equity_html.py` 一致）；**不要**在无理由时引入第二套绘图库（如 matplotlib）。
- **终端**：**Rich**（面板、表格、Spinner）。
- **可选 Web**：**Vite + React 19 + Tailwind 4**；日志列表用 **[@chenglou/pretext](https://github.com/chenglou/pretext)** 折行 + **TanStack Virtual**；流式文本 **ref + rAF**；**FastAPI** 静态资源 + **`/api/run` SSE**；勿对 SSE gzip 缓冲。

## 延迟与性能（给用户建议时）

- 优先建议 **`JQ_LLM_STREAM=true`** 改善体感延迟（SSE 流式）。
- 默认已启用 **HTTP/2**（`h2`）与 **httpx 连接复用**；弱网可调 **`JQ_LLM_HTTP_CONNECT_TIMEOUT`**。
- 语义检索对 **`index build`** 生成的大 JSON 有 **进程内 mtime 缓存**，无需改配置。

## MCP 集成提示

- 入口：`jq_agent/mcp_stdio.py`，使用 **`FastMCP`** 暴露与 `ToolDispatcher` 一致的工具（含 IDE 工具）。
- 在宿主（如 Cursor）中配置 **stdio** 命令指向：`jq-agent mcp-stdio`（需已安装 `[mcp]` 依赖）。

## 文档入口

- 人类可读总览：**[README.md](README.md)**（英文为主）、**[README.zh-CN.md](README.zh-CN.md)**（中文）。
- 架构、性能、可视化、路线图：见 README 内 **Architecture**、**Performance**、**Visualization stack**、**Roadmap**、**IDE Agent**、**对比（claw-code / Kilo Code）** 等章节。

## 免责声明

本仓库用于研究与学习；不构成投资建议。合规与数据授权由用户自行负责。
