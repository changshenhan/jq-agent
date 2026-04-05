"""任务路由：无额外 LLM 调用，用关键词/正则识别 jqdatasdk·聚宽相关任务（主流 fast-path 模式）。"""

from __future__ import annotations

import re

from jq_agent.config import Settings

# 覆盖常见 API 名、生态词与中文场景（偏召回，宁可多进 fast-path）
_JQ_SDK_PATTERNS: tuple[str, ...] = (
    r"jqdatasdk",
    r"joinquant",
    r"jqdata",
    r"get_price",
    r"get_fundamentals",
    r"get_all_securities",
    r"get_query_count",
    r"get_trade_days",
    r"set_benchmark",
    r"get_extras",
    r"order_target",
    r"order_value",
    r"run_daily",
    r"handle_data",
    r"g\.?ft\b",
    r"query_bar",
    r"聚宽",
    r"回测",
    r"模拟交易",
    r"沪深300",
    r"中证",
    r"tick 数据",
    r"k线",
    r"k 线",
)

# 中文整词（避免误伤）
_ZH_SUBSTR: tuple[str, ...] = ("聚宽", "回测", "jqdatasdk", "行情接口", "股票代码", "期货主力")


def detect_jq_sdk_intent(user_prompt: str) -> bool:
    """若用户描述明显与 jqdatasdk / 聚宽相关，返回 True。"""
    raw = user_prompt or ""
    if not raw.strip():
        return False
    low = raw.lower()
    for pat in _JQ_SDK_PATTERNS:
        if re.search(pat, low, re.I):
            return True
    for s in _ZH_SUBSTR:
        if s in raw:
            return True
    return False


def effective_jq_sdk_fast_path(settings: Settings, user_prompt: str) -> bool:
    """
    是否注入「jqdatasdk 快速路径」系统片段。
    - jq_sdk：始终注入
    - general：永不注入
    - auto：由 detect_jq_sdk_intent 决定
    """
    mode = settings.agent_task_mode
    if mode == "jq_sdk":
        return True
    if mode == "general":
        return False
    return detect_jq_sdk_intent(user_prompt)
