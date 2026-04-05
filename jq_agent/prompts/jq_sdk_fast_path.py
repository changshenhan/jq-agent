"""jqdatasdk / 聚宽任务专用系统片段（稳定前缀，利于底座 prompt cache 与首轮工具选择）。"""

from __future__ import annotations

from jq_agent.i18n import UiLang

ADDON_ZH = (
    "【jqdatasdk / 聚宽 · 快速路径】（路由增强；请严格按顺序执行以缩短无效轮次）\n"
    "1. **第一轮必须先调用 query_jq_docs**：用用户问题里的函数名、场景或错误信息作为 "
    "`question`，拿到官方片段后再写代码。\n"
    "2. 策略路径 **`scratchpad/*.py`**；文件头须 `from jqdatasdk import *`、`import os` 与 "
    "`auth(os.getenv(\"JQ_PHONE\"), os.getenv(\"JQ_PASSWORD\"))`。\n"
    "3. **execute_backtest** 依赖运行环境已配置 **`JQ_PHONE`** 与 **`JQ_PASSWORD`**"
    "（与 `.env` 一致）；未配置则明确告知用户，不要假装已回测。\n"
    "4. 除非用户明确要求检索 GitHub 仓库或用户主页，否则**不要调用 github_*** 工具，以免浪费轮次。\n"
    "5. 文档与语义检索依赖 **`JQ_LLM_API_KEY`** 与（可选）`jq-agent index build`；"
    "流式输出由 **`JQ_LLM_STREAM`** 控制，首字更快。"
)

ADDON_EN = (
    "【jqdatasdk / JoinQuant · fast path】 (router-enforced; minimize wasted turns)\n"
    "1. **First turn MUST call query_jq_docs** with the user’s API/symbol/error context "
    "as `question` before writing code.\n"
    "2. Strategies under **`scratchpad/*.py`**; header must include "
    "`from jqdatasdk import *`, `import os`, and "
    "`auth(os.getenv(\"JQ_PHONE\"), os.getenv(\"JQ_PASSWORD\"))`.\n"
    "3. **execute_backtest** requires **`JQ_PHONE`** and **`JQ_PASSWORD`** in the "
    "environment; if missing, say so—do not fake results.\n"
    "4. Do **not** call **github_*** tools unless the user explicitly asks for "
    "GitHub search/profile.\n"
    "5. Doc retrieval needs **`JQ_LLM_API_KEY`** and optional `jq-agent index build`; "
    "streaming is controlled by **`JQ_LLM_STREAM`**."
)


def jq_sdk_fast_path_addon(ui_lang: UiLang) -> str:
    return ADDON_ZH if ui_lang == "zh" else ADDON_EN
