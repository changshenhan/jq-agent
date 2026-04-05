from __future__ import annotations

from pathlib import Path

from jq_agent.config import Settings


def jq_agent_home() -> Path:
    p = Path.home() / ".jq-agent"
    p.mkdir(parents=True, exist_ok=True)
    return p


def jqdatasdk_index_dir(settings: Settings | None = None) -> Path:
    """文档切片与 embeddings 根目录；未配置 JQ_DOC_INDEX_DIR 时为用户目录下默认路径。"""
    if settings is not None:
        raw = (settings.doc_index_dir or "").strip()
        if raw:
            p = Path(raw).expanduser()
            if not p.is_absolute():
                p = Path.cwd() / p
            p.mkdir(parents=True, exist_ok=True)
            return p
    d = jq_agent_home() / "jqdatasdk_index"
    d.mkdir(parents=True, exist_ok=True)
    return d


def chunks_json_path(settings: Settings | None = None) -> Path:
    return jqdatasdk_index_dir(settings) / "chunks.json"


def embeddings_json_path(settings: Settings | None = None) -> Path:
    return jqdatasdk_index_dir(settings) / "embeddings.json"


def index_meta_path(settings: Settings | None = None) -> Path:
    """写入 metadata 的路径（与 chunks 同目录）。"""
    return jqdatasdk_index_dir(settings) / "index_meta.json"


def index_meta_read_path(settings: Settings | None = None) -> Path:
    """读取 metadata：优先新位置，兼容旧版 ~/.jq-agent/index_meta.json。"""
    p = index_meta_path(settings)
    if p.exists():
        return p
    legacy = jq_agent_home() / "index_meta.json"
    if legacy.exists():
        return legacy
    return p


def cache_src_dir() -> Path:
    d = jq_agent_home() / "cache" / "jqdatasdk-src"
    d.mkdir(parents=True, exist_ok=True)
    return d
