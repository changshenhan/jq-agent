from __future__ import annotations

from pathlib import Path


def jq_agent_home() -> Path:
    p = Path.home() / ".jq-agent"
    p.mkdir(parents=True, exist_ok=True)
    return p


def jqdatasdk_index_dir() -> Path:
    d = jq_agent_home() / "jqdatasdk_index"
    d.mkdir(parents=True, exist_ok=True)
    return d


def chunks_json_path() -> Path:
    return jqdatasdk_index_dir() / "chunks.json"


def embeddings_json_path() -> Path:
    return jqdatasdk_index_dir() / "embeddings.json"


def index_meta_path() -> Path:
    return jq_agent_home() / "index_meta.json"


def cache_src_dir() -> Path:
    d = jq_agent_home() / "cache" / "jqdatasdk-src"
    d.mkdir(parents=True, exist_ok=True)
    return d
