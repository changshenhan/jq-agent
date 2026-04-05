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
    if updates:
        return s.model_copy(update=updates)
    return s
