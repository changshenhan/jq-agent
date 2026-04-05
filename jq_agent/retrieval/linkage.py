"""文档检索能力说明：与 `index build` / `query_jq_docs` 显式联动。"""

from __future__ import annotations

from typing import Any

from jq_agent.i18n import UiLang, t


def safe_index_status() -> dict[str, Any]:
    """索引状态（关键词内置片段 + 可选 API 语义缓存）。"""
    try:
        from jq_agent.indexing.vector_build import index_status

        return index_status()
    except OSError:
        return {"chunks_exists": False, "embeddings_exists": False}


def system_prompt_retrieval_addon(ui_lang: UiLang) -> str:
    """拼入 LLM system，告知 query_jq_docs 当前检索模式。"""
    st = safe_index_status()
    emb = bool(st.get("embeddings_exists"))
    cc = int(st.get("chunk_count") or 0)
    if emb and cc > 0:
        return t("sys_retrieval_semantic_ready", ui_lang, n=cc)
    if cc > 0:
        return t("sys_retrieval_chunks_only", ui_lang, n=cc)
    return t("sys_retrieval_bundled_only", ui_lang)


def doctor_retrieval_lines(ui_lang: UiLang) -> list[str]:
    """doctor 子命令输出的多行文案。"""
    st = safe_index_status()
    lines: list[str] = []
    lines.append(t("doctor_doc_retrieval", ui_lang))
    cc = int(st.get("chunk_count") or 0)
    emb = bool(st.get("embeddings_exists"))
    if cc > 0:
        lines.append(t("doctor_chunks_ready", ui_lang, n=cc))
    else:
        lines.append(t("doctor_chunks_builtin", ui_lang))
    if emb:
        lines.append(t("doctor_embeddings_ready", ui_lang))
    else:
        lines.append(t("doctor_embeddings_hint", ui_lang))
    meta = st.get("meta") if isinstance(st.get("meta"), dict) else {}
    if meta.get("built_at"):
        lines.append(t("doctor_index_built", ui_lang, at=str(meta.get("built_at", ""))))
    return lines
