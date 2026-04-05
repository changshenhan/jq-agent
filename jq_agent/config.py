from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """环境变量配置；密钥不得写入策略文件或仓库。"""

    model_config = SettingsConfigDict(env_prefix="JQ_", env_file=".env", extra="ignore")

    llm_api_key: str = Field(
        default="",
        description="底座模型 API Key（OpenAI 兼容 Chat/Embeddings，如 DeepSeek、OpenRouter 等）",
    )
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI 兼容 API 根 URL（chat 与 embeddings 同前缀）",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embeddings 模型 id（POST /v1/embeddings）",
    )
    model: str = Field(default="gpt-4o-mini", description="chat completions 模型 id")

    phone: str = Field(default="", description="聚宽账号（JQ_PHONE；execute_backtest / jqdatasdk 子进程）")
    password: str = Field(default="", description="聚宽密码（对应环境变量 JQ_PASSWORD）")

    max_iterations: int = Field(default=16, ge=1, le=64, description="Agent 循环上限（熔断）")
    backtest_timeout_sec: float = Field(default=120.0, ge=1.0, description="子进程回测超时")

    sandbox_dir: Path = Field(
        default_factory=lambda: Path.cwd() / ".jq-agent",
        description="Agent 工作区根目录（含 sandbox/、scratchpad/ 等子路径，工具路径须落在此之下）",
    )

    llm_stream: bool = Field(
        default=False,
        description="是否对 LLM 使用 SSE 流式输出（首字延迟更低）",
    )
    permission_mode: Literal["normal", "strict"] = Field(
        default="normal",
        description="strict 时 write_strategy_file 仅允许 scratchpad/ 前缀",
    )
    usage_log: bool = Field(
        default=True,
        description="是否将 token 用量追加写入 ~/.jq-agent/usage.jsonl",
    )
    auto_parse_backtest_metrics: bool = Field(
        default=True,
        description="execute_backtest 成功后是否自动解析 stdout 中的 BACKTEST_METRICS_JSON",
    )

    session_backend: Literal["json", "sqlite"] = Field(
        default="sqlite",
        description="会话存储：json 文件或 SQLite（~/.jq-agent/jq_agent.sqlite3）",
    )
    session_compact_threshold: int = Field(
        default=40,
        ge=10,
        le=200,
        description="消息条数超过该值则触发压缩（需有效 API Key）",
    )
    session_compact_keep: int = Field(
        default=12,
        ge=4,
        le=64,
        description="压缩后保留尾部消息条数",
    )

    ide_agent_tools: bool = Field(
        default=True,
        description="启用 IDE 级工具：列目录、glob、grep、search_replace、run_terminal_cmd（对标 Kilocode 工作区能力）",
    )
    terminal_timeout_sec: float = Field(
        default=120.0,
        ge=5.0,
        le=600.0,
        description="run_terminal_cmd 子进程超时（秒）",
    )
    terminal_max_output_chars: int = Field(
        default=48_000,
        ge=4_000,
        le=500_000,
        description="run_terminal_cmd 合并 stdout+stderr 最大字符数，超出截断",
    )

    # --- LLM HTTP 客户端（延迟与吞吐：HTTP/2、连接池、分阶段超时）---
    llm_http_connect_timeout: float = Field(
        default=15.0,
        ge=1.0,
        le=120.0,
        description="连接底座超时（秒）；过短易误判弱网，过长拖慢失败检测",
    )
    llm_http_read_timeout: float = Field(
        default=300.0,
        ge=30.0,
        le=3600.0,
        description="读响应超时（秒）；长思维链/大输出需足够大",
    )
    llm_http_keepalive: int = Field(
        default=32,
        ge=4,
        le=256,
        description="httpx keep-alive 连接池大小（多轮对话复用连接）",
    )
    llm_http_max_connections: int = Field(
        default=100,
        ge=8,
        le=512,
        description="httpx 最大并发连接数上限",
    )
    llm_http2: bool = Field(
        default=True,
        description="启用 HTTP/2（需依赖 h2；多路复用，与 OpenAI/兼容网关主流实践一致）",
    )

    # --- GitHub 公开 API（仅 api.github.com：搜索仓库/用户、查看公开资料）---
    github_tools_enabled: bool = Field(
        default=True,
        description="启用 github_* 工具（REST API；匿名有速率限制，可选 token）",
    )
    github_token: str = Field(
        default="",
        description="可选 GitHub PAT/fine-grained token，提高 API 配额（也可用环境变量 GITHUB_TOKEN）",
    )


def load_settings() -> Settings:
    """读取配置；兼容旧环境变量 JQ_OPENAI_API_KEY / JQ_OPENAI_BASE_URL。"""
    s = Settings()
    updates: dict = {}
    if not s.llm_api_key.strip():
        leg = os.environ.get("JQ_OPENAI_API_KEY", "").strip()
        if leg:
            updates["llm_api_key"] = leg
    if not os.environ.get("JQ_LLM_BASE_URL") and os.environ.get("JQ_OPENAI_BASE_URL"):
        leg_u = os.environ.get("JQ_OPENAI_BASE_URL", "").strip()
        if leg_u:
            updates["llm_base_url"] = leg_u
    if not s.github_token.strip():
        gt = os.environ.get("GITHUB_TOKEN", "").strip()
        if gt:
            updates["github_token"] = gt

    if "JQ_GITHUB_TOOLS" in os.environ:
        raw = os.environ.get("JQ_GITHUB_TOOLS", "").strip().lower()
        updates["github_tools_enabled"] = raw in ("1", "true", "yes", "on")

    if updates:
        return s.model_copy(update=updates)
    return s
