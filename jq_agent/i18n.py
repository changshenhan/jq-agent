"""CLI 与运行期 UI 文案（zh / en）；与模型 system prompt 解耦。"""

from __future__ import annotations

from typing import Literal

UiLang = Literal["zh", "en"]

STRINGS: dict[str, dict[str, str]] = {
    "app_help": {
        "zh": "jq-agent — 聚宽生态量化 Agent 开源框架（编排 + 工具 + 文档检索）",
        "en": "jq-agent — open-source JoinQuant-style quant Agent (orchestration + tools + doc retrieval)",
    },
    "opt_lang_help": {
        "zh": "界面语言：zh（中文）或 en（英文）；也可设环境变量 JQ_LANG",
        "en": "UI language: zh or en; or set env JQ_LANG",
    },
    "cmd_run_help": {
        "zh": "运行 Agent 闭环（需配置底座模型 JQ_LLM_API_KEY 等）",
        "en": "Run the agent loop (requires JQ_LLM_API_KEY or compatible provider key)",
    },
    "arg_prompt_help": {
        "zh": "自然语言任务描述",
        "en": "Task in natural language",
    },
    "opt_model_help": {
        "zh": "覆盖 JQ_MODEL",
        "en": "Override JQ_MODEL",
    },
    "opt_max_iter_help": {
        "zh": "覆盖最大循环次数",
        "en": "Override max agent iterations",
    },
    "cmd_doctor_help": {
        "zh": "检查环境与沙箱路径（不调用模型）",
        "en": "Check environment and sandbox (no LLM call)",
    },
    "cmd_config_help": {
        "zh": "读写界面语言等本地偏好（~/.jq-agent/settings.json）",
        "en": "Read/write UI preferences (~/.jq-agent/settings.json)",
    },
    "config_lang_help": {
        "zh": "将界面语言设为 zh 或 en 并写入本地配置",
        "en": "Persist UI language as zh or en",
    },
    "iteration_line": {
        "zh": "--- 第 {cur}/{total} 轮 ---",
        "en": "--- iteration {cur}/{total} ---",
    },
    "tool_line": {
        "zh": "工具",
        "en": "TOOL",
    },
    "stopped": {
        "zh": "停止原因",
        "en": "Stopped",
    },
    "iterations_suffix": {
        "zh": "轮次",
        "en": "iterations",
    },
    "reason_missing_key": {
        "zh": "缺少 API Key：请设置环境变量 JQ_LLM_API_KEY（或旧名 JQ_OPENAI_API_KEY）",
        "en": "Missing API key: set JQ_LLM_API_KEY (legacy: JQ_OPENAI_API_KEY)",
    },
    "reason_done": {
        "zh": "已完成（本轮无工具调用）",
        "en": "completed (no tool calls in this round)",
    },
    "reason_max_iter": {
        "zh": "已达最大循环次数",
        "en": "max iterations reached",
    },
    "reason_llm_error": {
        "zh": "LLM 请求失败：{detail}",
        "en": "LLM request failed: {detail}",
    },
    "doctor_title": {
        "zh": "jq-agent 环境诊断",
        "en": "jq-agent environment",
    },
    "doctor_sandbox": {
        "zh": "沙箱目录",
        "en": "Sandbox",
    },
    "doctor_key": {
        "zh": "API Key",
        "en": "API Key",
    },
    "doctor_key_set": {
        "zh": "已设置",
        "en": "set",
    },
    "doctor_key_unset": {
        "zh": "未设置（请配置 JQ_LLM_API_KEY）",
        "en": "not set (configure JQ_LLM_API_KEY)",
    },
    "doctor_model": {
        "zh": "模型",
        "en": "Model",
    },
    "doctor_base_url": {
        "zh": "Base URL",
        "en": "Base URL",
    },
    "doctor_max_iter": {
        "zh": "最大循环次数",
        "en": "Max iterations",
    },
    "doctor_ui_lang": {
        "zh": "界面语言",
        "en": "UI language",
    },
    "config_saved": {
        "zh": "已保存界面语言：{lang}",
        "en": "Saved UI language: {lang}",
    },
    "config_current": {
        "zh": "当前界面语言：{lang}（配置文件：{path}）",
        "en": "Current UI language: {lang} (config: {path})",
    },
    "err_lang_invalid": {
        "zh": "语言必须是 zh 或 en",
        "en": "language must be zh or en",
    },
    # 文档检索（内置关键词 + 可选底座 Embeddings API）
    "sys_retrieval_semantic_ready": {
        "zh": "【文档检索】已构建切片（约 {n} 条）且含 API 语义缓存，query_jq_docs 将语义与关键词混合。",
        "en": (
            "[Docs] ~{n} chunks built with embedding cache; query_jq_docs mixes semantic + keyword hits."
        ),
    },
    "sys_retrieval_chunks_only": {
        "zh": (
            "【文档检索】已构建切片（约 {n} 条），无 Embeddings 缓存时 query_jq_docs 以关键词为主。"
            "配置 JQ_LLM_API_KEY 后重建索引可启用语义。"
        ),
        "en": (
            "[Docs] ~{n} chunks on disk; keyword-heavy until you rebuild with JQ_LLM_API_KEY for embeddings."
        ),
    },
    "sys_retrieval_bundled_only": {
        "zh": "【文档检索】使用内置关键词片段；构建：jq-agent index build（可选配 JQ_LLM_API_KEY 生成语义缓存）。",
        "en": (
            "[Docs] Bundled keyword snippets only; run jq-agent index build (optional JQ_LLM_API_KEY for embeddings)."
        ),
    },
    "doctor_doc_retrieval": {
        "zh": "── 文档检索（与 query_jq_docs 联动）──",
        "en": "── Doc retrieval (query_jq_docs) ──",
    },
    "doctor_chunks_ready": {
        "zh": "切片索引：约 {n} 条（~/.jq-agent/jqdatasdk_index/chunks.json）",
        "en": "Chunk index: ~{n} entries (~/.jq-agent/jqdatasdk_index/chunks.json)",
    },
    "doctor_chunks_builtin": {
        "zh": "切片索引：未构建（query_jq_docs 使用内置 doc_chunks 关键词）",
        "en": "Chunk index: not built (query_jq_docs uses bundled keyword snippets)",
    },
    "doctor_embeddings_ready": {
        "zh": "语义缓存：已生成（Embeddings API，与关键词混合）",
        "en": "Embedding cache: present (via provider Embeddings API)",
    },
    "doctor_embeddings_hint": {
        "zh": "语义缓存：无（设置 JQ_LLM_API_KEY 后执行 jq-agent index build 可生成）",
        "en": "Embedding cache: none (set JQ_LLM_API_KEY and run jq-agent index build)",
    },
    "doctor_index_built": {
        "zh": "上次构建时间：{at}",
        "en": "Last built: {at}",
    },
}


def t(key: str, ui_lang: UiLang, **kwargs: str | int) -> str:
    row = STRINGS.get(key, {})
    base = row.get(ui_lang) or row.get("en") or key
    if kwargs:
        try:
            return base.format(**kwargs)
        except (KeyError, ValueError):
            return base
    return base


def normalize_lang(value: str | None) -> UiLang:
    if not value:
        return "zh"
    v = value.strip().lower()
    if v in ("zh", "zh-cn", "cn", "chinese"):
        return "zh"
    if v in ("en", "en-us", "english"):
        return "en"
    return "zh"
