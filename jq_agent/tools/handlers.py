from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from typing import Any

from jq_agent.config import Settings
from jq_agent.linting import run_ruff_check
from jq_agent.llm.subtask import run_research_subtask_async
from jq_agent.permissions import PathPolicy
from jq_agent.retrieval.local import keyword_search, load_merged_chunks
from jq_agent.tools.json_repair import parse_tool_arguments


class ToolDispatcher:
    def __init__(
        self,
        settings: Settings,
        *,
        ui_lang: str = "zh",
        active_session: str | None = None,
    ) -> None:
        self.settings = settings
        self._ui_lang = ui_lang
        self._active_session = active_session
        self.policy = PathPolicy(settings.sandbox_dir)
        self.policy.mkdir()
        self._chunks = load_merged_chunks()

    def dispatch(self, name: str, arguments: str) -> str:
        args, jerr = parse_tool_arguments(arguments or "")
        if args is None:
            return json.dumps(
                {"error": "invalid_tool_arguments_json", "detail": jerr or "parse_failed"},
                ensure_ascii=False,
            )

        try:
            if name == "query_jq_docs":
                return self._query_jq_docs(args.get("question", ""))
            if name == "read_file":
                return self._read_file(args.get("path", ""))
            if name == "write_strategy_file":
                return self._write_strategy(args.get("path", ""), args.get("content", ""))
            if name == "execute_backtest":
                return self._execute_backtest(args.get("file_path", ""))
            if name == "analyze_backtest_metrics":
                return self._analyze_metrics(
                    args.get("metrics_json") or "{}",
                    args.get("stdout_text") or "",
                )
            if name == "lint_strategy_file":
                return self._lint_strategy(args.get("path", ""))
            if name == "research_subtask":
                return self._research_subtask(args.get("task", ""))
            if name == "fork_subagent_session":
                return self._fork_subagent(args.get("child_slug", ""))
        except PermissionError as e:
            return json.dumps({"error": "permission_denied", "detail": str(e)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": "tool_failed", "detail": str(e)}, ensure_ascii=False)

        return json.dumps({"error": "unknown_tool", "name": name}, ensure_ascii=False)

    def _strict_check_write(self, rel: str) -> None:
        if self.settings.permission_mode != "strict":
            return
        norm = rel.replace("\\", "/").lstrip("/")
        if not norm.startswith("scratchpad/"):
            raise PermissionError(
                "JQ_PERMISSION_MODE=strict 时仅允许写入 scratchpad/ 下文件，收到: " + rel
            )

    def _query_jq_docs(self, question: str) -> str:
        vec_raw: list[dict[str, Any]] = []
        try:
            from jq_agent.retrieval.semantic import semantic_hits

            vec_raw = semantic_hits(question, self.settings, top_k=8)
        except Exception:
            vec_raw = []

        kw_hits = keyword_search(question, self._chunks, top_k=5)
        out_rows: list[dict[str, Any]] = []
        seen: set[str] = set()

        for h in vec_raw:
            cid = str(h.get("chunk_id", ""))
            if not cid or cid in seen:
                continue
            seen.add(cid)
            out_rows.append(
                {
                    "chunk_id": cid,
                    "source": h.get("source", ""),
                    "version": h.get("version", ""),
                    "score": float(h.get("score", 0)),
                    "text": h.get("text", ""),
                }
            )

        for h in kw_hits:
            if h.chunk_id in seen:
                continue
            seen.add(h.chunk_id)
            out_rows.append(
                {
                    "chunk_id": h.chunk_id,
                    "source": h.source,
                    "version": h.version,
                    "score": float(h.score),
                    "text": h.text,
                }
            )
            if len(out_rows) >= 10:
                break

        if vec_raw and kw_hits:
            mode = "hybrid"
        elif vec_raw:
            mode = "vector"
        else:
            mode = "keyword"

        if not out_rows:
            return json.dumps(
                {
                    "hits": [],
                    "retrieval": "none",
                    "notice": (
                        "无命中；可运行 `jq-agent index build` 拉取官方源码切片并可选写入 Embeddings 缓存，"
                        "或缩小问题。"
                    ),
                },
                ensure_ascii=False,
            )

        guidance = (
            "检索到官方 SDK 片段：编写代码时请优先使用上述命中里出现的函数名与参数形式，"
            "必要时对照片段中的签名；不要臆造不存在的 API。"
        )
        return json.dumps(
            {
                "hits": out_rows[:10],
                "retrieval": mode,
                "guidance": guidance,
            },
            ensure_ascii=False,
        )

    def _read_file(self, path: str) -> str:
        p = self.policy.ensure_under_sandbox(path)
        if not p.exists():
            return json.dumps({"error": "not_found", "path": str(p)}, ensure_ascii=False)
        return json.dumps(
            {"path": str(p), "content": p.read_text(encoding="utf-8", errors="replace")},
            ensure_ascii=False,
        )

    def _write_strategy(self, path: str, content: str) -> str:
        self._strict_check_write(path)
        p = self.policy.ensure_under_sandbox(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return json.dumps({"written": str(p), "bytes": len(content.encode("utf-8"))}, ensure_ascii=False)

    def _lint_strategy(self, path: str) -> str:
        if not path.strip():
            return json.dumps({"error": "empty_path"}, ensure_ascii=False)
        p = self.policy.ensure_under_sandbox(path)
        if not p.exists():
            return json.dumps({"error": "not_found", "path": str(p)}, ensure_ascii=False)
        if p.suffix.lower() != ".py":
            return json.dumps({"error": "expected_python_file", "path": str(p)}, ensure_ascii=False)
        r = run_ruff_check(p)
        return json.dumps(r, ensure_ascii=False)

    def _research_subtask(self, task: str) -> str:
        if not task.strip():
            return json.dumps({"error": "empty_task"}, ensure_ascii=False)
        text = asyncio.run(
            run_research_subtask_async(self.settings, task.strip(), self._ui_lang),
        )
        return json.dumps({"subtask_result": text}, ensure_ascii=False)

    def _fork_subagent(self, child_slug: str) -> str:
        if not self._active_session:
            return json.dumps(
                {
                    "error": "no_active_session",
                    "detail": "仅在 jq-agent run --session NAME 时可在树中分叉子会话。",
                },
                ensure_ascii=False,
            )
        if not child_slug.strip():
            return json.dumps({"error": "empty_child_slug"}, ensure_ascii=False)
        from jq_agent.storage.sqlite_store import fork_child

        child = fork_child(self._active_session, child_slug.strip())
        return json.dumps(
            {
                "child_session": child,
                "hint": f'子会话已创建。继续对话：jq-agent run --session {child} --resume "..."',
            },
            ensure_ascii=False,
        )

    def _execute_backtest(self, file_path: str) -> str:
        p = self.policy.ensure_under_sandbox(file_path)
        if not p.exists():
            return json.dumps({"error": "not_found", "path": str(p)}, ensure_ascii=False)
        if p.suffix.lower() != ".py":
            return json.dumps({"error": "expected_python_file", "path": str(p)}, ensure_ascii=False)

        phone = (self.settings.phone or os.environ.get("JQ_PHONE") or "").strip()
        password = (self.settings.password or os.environ.get("JQ_PASSWORD") or "").strip()
        if not phone or not password:
            return json.dumps(
                {
                    "error": "missing_joinquant_credentials",
                    "detail": "执行依赖聚宽账号：请设置环境变量 JQ_PHONE 与 JQ_PASSWORD。",
                    "hint": (
                        "在 jq-agent 项目根目录创建或编辑 .env（勿提交到 Git），添加：\n"
                        "  JQ_PHONE=你的手机号或账号\n"
                        "  JQ_PASSWORD=你的密码\n"
                        "然后在本机同一 shell 中运行 jq-agent，或确保进程继承上述环境变量。"
                    ),
                    "path": str(p),
                },
                ensure_ascii=False,
            )

        try:
            child_env = {**os.environ, "JQ_PHONE": phone, "JQ_PASSWORD": password}
            proc = subprocess.run(
                [sys.executable, str(p)],
                cwd=str(self.policy.root),
                env=child_env,
                capture_output=True,
                text=True,
                timeout=self.settings.backtest_timeout_sec,
            )
        except subprocess.TimeoutExpired:
            return json.dumps(
                {
                    "error": "timeout",
                    "seconds": self.settings.backtest_timeout_sec,
                    "path": str(p),
                },
                ensure_ascii=False,
            )

        out_obj: dict[str, Any] = {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-8000:] if proc.stdout else "",
            "stderr": proc.stderr[-8000:] if proc.stderr else "",
            "path": str(p),
            "note": (
                "可将本结果的 stdout 传给 analyze_backtest_metrics(stdout_text=...) "
                "以解析 BACKTEST_METRICS_JSON 等指标并进入下一轮优化。"
            ),
        }
        if self.settings.auto_parse_backtest_metrics and proc.stdout:
            parsed = _parse_metrics_from_stdout(proc.stdout)
            if parsed:
                out_obj["auto_parsed_metrics"] = parsed
                out_obj["data_loop_hint"] = (
                    "已从 stdout 自动解析指标（auto_parsed_metrics），"
                    "可直接用于优化策略或再调 analyze_backtest_metrics。"
                )

        if proc.returncode == 0:
            from jq_agent.tools.equity_html import try_generate_equity_html

            extra = try_generate_equity_html(self.policy)
            if extra:
                out_obj.update(extra)

        return json.dumps(out_obj, ensure_ascii=False)

    def _analyze_metrics(self, metrics_json: str, stdout_text: str) -> str:
        parsed_stdout = _parse_metrics_from_stdout(stdout_text)
        explicit: dict[str, Any] = {}
        if metrics_json.strip():
            try:
                raw = json.loads(metrics_json)
                if isinstance(raw, dict):
                    explicit = raw
                else:
                    explicit = {"value": raw}
            except json.JSONDecodeError as e:
                return json.dumps({"error": "invalid_metrics_json", "detail": str(e)}, ensure_ascii=False)

        merged: dict[str, Any] = {**parsed_stdout, **explicit}
        if not merged:
            return json.dumps(
                {
                    "error": "empty_metrics",
                    "detail": "请至少提供 metrics_json，或传入 execute_backtest 返回的 stdout 片段作为 stdout_text。",
                },
                ensure_ascii=False,
            )

        sharpe_keys = ("sharpe_ratio", "sharpe")
        dd_keys = ("max_drawdown", "max_dd")
        sharpe_v = next((merged[k] for k in sharpe_keys if k in merged), None)
        dd_v = next((merged[k] for k in dd_keys if k in merged), None)
        next_hint = (
            "已结构化指标，可据此调整参数、止损或因子；若夏普偏低或回撤过大，"
            "建议 query_jq_docs 核对 API 后改写策略并再次 execute_backtest。"
        )
        if sharpe_v is not None or dd_v is not None:
            next_hint += f" 当前关注：sharpe≈{sharpe_v!s}，max_drawdown≈{dd_v!s}。"

        return json.dumps(
            {
                "accepted": True,
                "metrics": merged,
                "parsed_from_stdout": bool(parsed_stdout),
                "overrides_from_explicit_json": bool(explicit),
                "hint": "可结合夏普、最大回撤、年化等判断是否需改参数或换因子。",
                "next_optimization_hint": next_hint,
            },
            ensure_ascii=False,
        )


def _parse_metrics_from_stdout(stdout: str) -> dict[str, Any]:
    """解析子进程打印的 BACKTEST_METRICS_JSON: {...} 及常见 JSON 行。"""
    out: dict[str, Any] = {}
    if not stdout or not stdout.strip():
        return out

    marker = "BACKTEST_METRICS_JSON:"
    for line in stdout.splitlines():
        line = line.strip()
        if marker in line:
            idx = line.index(marker)
            rest = line[idx + len(marker) :].strip()
            try:
                data = json.loads(rest)
                if isinstance(data, dict):
                    out.update(data)
            except json.JSONDecodeError:
                continue

    if not out:
        m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", stdout, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                if isinstance(data, dict):
                    out.update(data)
            except json.JSONDecodeError:
                pass

    return out
