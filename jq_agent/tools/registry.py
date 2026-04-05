from __future__ import annotations

from typing import Any


def openai_tools() -> list[dict[str, Any]]:
    """OpenAI Chat Completions `tools` 列表（JSON Schema）。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "query_jq_docs",
                "description": (
                    "从关键词库与（若已 index build）底座模型 Embeddings API 缓存检索 jqdatasdk 官方源码片段。"
                    "命中后必须优先使用片段中的函数名、参数表与示例，避免臆造 API。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "要问的问题，例如 get_price 参数、get_query_count、沪深300代码",
                        }
                    },
                    "required": ["question"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "在 Agent 工作区（.jq-agent 根下）读取文本文件，例如 scratchpad 或 sandbox 内脚本。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "相对工作区根的路径，例如 scratchpad/demo.py",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_strategy_file",
                "description": (
                    "在工作区内写入或覆盖策略 Python 文件。聚宽策略请优先使用路径 scratchpad/<name>.py；"
                    "内容须含 jqdatasdk 与 auth(os.getenv(...)) 约定（见 system 提示）。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "相对工作区根路径，推荐 scratchpad/strategy.py",
                        },
                        "content": {"type": "string", "description": "完整文件内容"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "execute_backtest",
                "description": (
                    "在工作区根目录下用 python 子进程执行策略文件，捕获 stdout/stderr/退出码。"
                    "运行前会检查环境变量 JQ_PHONE 与 JQ_PASSWORD；缺失则返回错误指引，不盲目执行。"
                    "策略应在 stdout 中打印 BACKTEST_METRICS_JSON；并在成功时将净值序列写入 "
                    "scratchpad/backtest_equity.csv，以便生成 scratchpad/backtest_result.html 交互式净值图。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "相对工作区的策略路径，如 scratchpad/foo.py",
                        }
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_backtest_metrics",
                "description": (
                    "解析并汇总回测指标，供下一轮策略优化。可将 execute_backtest 返回的 stdout 原样传入"
                    " stdout_text，以自动解析其中的 BACKTEST_METRICS_JSON 行及内嵌 JSON；"
                    "也可额外传入 metrics_json 覆盖或补充字段（后者优先）。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "stdout_text": {
                            "type": "string",
                            "description": "execute_backtest 工具返回的 stdout 全文或片段，用于提取夏普、回撤等",
                        },
                        "metrics_json": {
                            "type": "string",
                            "description": (
                                "可选。显式 JSON 对象字符串（含 sharpe、max_drawdown 等）；"
                                "与 stdout 解析结果合并，本字段优先覆盖同名字段。"
                            ),
                        },
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "lint_strategy_file",
                "description": (
                    "对沙箱内 .py 策略运行 ruff check（若已安装 ruff）。"
                    "用于在回测前发现语法/风格问题，减少无效 execute_backtest 轮次。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "相对工作区根的 Python 文件路径",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "research_subtask",
                "description": (
                    "无工具的单轮 LLM 子任务：用于拆解复杂推理、总结因子思路等。"
                    "不访问文件系统；主循环仍应通过其他工具落盘与执行。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "要讨论的子问题（中文或英文）",
                        }
                    },
                    "required": ["task"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fork_subagent_session",
                "description": (
                    "在当前会话树中创建子会话（需主 CLI 使用 --session）。"
                    "返回 child_session 名称，可用 jq-agent run --session <child> --resume 继续。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "child_slug": {
                            "type": "string",
                            "description": "子分支短名，如 factor-a、try2",
                        }
                    },
                    "required": ["child_slug"],
                },
            },
        },
    ]
