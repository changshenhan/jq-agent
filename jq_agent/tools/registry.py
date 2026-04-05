from __future__ import annotations

from typing import Any


def _github_tool_definitions() -> list[dict[str, Any]]:
    """GitHub REST API（仅公开数据；可选 token 提配额）。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "github_search_repositories",
                "description": (
                    "在 GitHub 上搜索公开仓库（GitHub Search API）。"
                    "q 支持官方语法，如 language:python、stars:>1000、user:orgname。"
                    "用于发现项目、对比 star 数、找文档/示例仓库。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词或复合条件，例如 jqdatasdk、quant stars:>50",
                        },
                        "sort": {
                            "type": "string",
                            "description": (
                                "排序：best-match（默认）、stars、forks、help-wanted-issues、updated"
                            ),
                        },
                        "order": {"type": "string", "description": "asc 或 desc，默认 desc"},
                        "per_page": {
                            "type": "integer",
                            "description": "每页条数 1–30，默认 10",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "github_search_users",
                "description": (
                    "在 GitHub 上搜索用户/组织（公开资料）。"
                    "可与 github_get_user 配合查看主页式字段。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "用户名关键词或 location:China 等",
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "每页条数 1–30，默认 10",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "github_get_user",
                "description": (
                    "获取 GitHub 用户或组织的公开主页信息（粉丝数、简介、仓库数、博客链接等）。"
                    "对应网页 https://github.com/<username> 的公开 API 数据。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "登录名，不含 @",
                        }
                    },
                    "required": ["username"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "github_get_repository",
                "description": (
                    "获取某公开仓库的元数据（描述、star、语言、默认分支、topics、许可证等）。"
                    "对应 github.com/owner/repo 的公开信息。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "仓库所有者登录名或组织名"},
                        "repo": {"type": "string", "description": "仓库名（不含 owner 前缀）"},
                    },
                    "required": ["owner", "repo"],
                },
            },
        },
    ]


def _ide_agent_tool_definitions() -> list[dict[str, Any]]:
    """Kilocode / IDE 风格：工作区浏览、搜索、局部编辑、沙箱终端。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": (
                    "列出沙箱工作区某目录下的直接子项（文件与子目录名）。"
                    "path 为空字符串表示工作区根。用于探索项目结构。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "相对工作区根的路径，如 scratchpad 或空字符串",
                        },
                        "max_entries": {
                            "type": "integer",
                            "description": "最多返回条目数，默认 200",
                        },
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "glob_files",
                "description": (
                    "在沙箱根目录下按 glob 模式枚举文件路径（如 **/*.py、scratchpad/**/*.py）。"
                    "结果截断至 500 条。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "glob 模式，相对工作区根",
                        }
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "grep_workspace",
                "description": (
                    "在沙箱内对文本文件做逐行正则搜索（默认扫描 **/*.py）。"
                    "用于定位符号、TODO、错误处理等。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "regex": {"type": "string", "description": "Python re 正则表达式"},
                        "file_glob": {
                            "type": "string",
                            "description": "文件 glob，默认 **/*.py",
                        },
                        "max_matches": {
                            "type": "integer",
                            "description": "最多返回匹配数，默认 40",
                        },
                    },
                    "required": ["regex"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_replace",
                "description": (
                    "在单个文件中将 old_string 唯一一次替换为 new_string（局部编辑，类似 IDE）。"
                    "若匹配 0 次或多次则失败；整文件重写仍可用 write_strategy_file。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "相对工作区根的文件路径"},
                        "old_string": {"type": "string", "description": "须唯一匹配的原文片段"},
                        "new_string": {"type": "string", "description": "替换后的内容"},
                    },
                    "required": ["path", "old_string", "new_string"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_terminal_cmd",
                "description": (
                    "在沙箱工作区根目录下执行一条命令（使用 shlex 解析，非交互式 shell；"
                    "禁止管道与重定向技巧逃逸沙箱）。"
                    "适用于 python -m、ruff、pytest 等。JQ_PERMISSION_MODE=strict 时禁用。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "单行命令，如 python scratchpad/foo.py 或 ruff check scratchpad/",
                        }
                    },
                    "required": ["command"],
                },
            },
        },
    ]


def openai_tools(*, ide_agent: bool = True, github_tools: bool = True) -> list[dict[str, Any]]:
    """OpenAI Chat Completions `tools` 列表（JSON Schema）。"""
    core: list[dict[str, Any]] = [
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
    if github_tools:
        core.extend(_github_tool_definitions())
    if ide_agent:
        core.extend(_ide_agent_tool_definitions())
    return core
