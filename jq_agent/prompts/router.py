"""按模型 / 服务商追加少量 system 片段（对标 Kilo 的 provider 路由，极简版）。"""

from __future__ import annotations


def model_system_addon(model: str, base_url: str) -> str:
    m = (model or "").lower()
    u = (base_url or "").lower()
    parts: list[str] = []
    if "deepseek" in u or "deepseek" in m:
        parts.append(
            "【模型提示】当前为 DeepSeek 兼容端点：工具调用请严格输出合法 JSON；"
            "不确定时先用 query_jq_docs。"
        )
    if "gpt-4" in m or "gpt-3.5" in m or "openai" in u:
        parts.append("【模型提示】OpenAI 系：遵守 function calling schema，参数用双引号 JSON。")
    if "qwen" in m or "dashscope" in u:
        parts.append("【模型提示】通义等：若工具调用失败可缩短并行工具数量并重试。")
    if not parts:
        parts.append("【模型提示】优先工具调用而非空答；遵守 JSON 参数格式。")
    return "\n".join(parts)
