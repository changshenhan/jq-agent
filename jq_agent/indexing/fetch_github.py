from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx

GITHUB_API = "https://api.github.com/repos/JoinQuant/jqdatasdk/contents/jqdatasdk"
RAW_BASE = "https://raw.githubusercontent.com/JoinQuant/jqdatasdk/master/jqdatasdk"

# 国内访问 raw.githubusercontent.com 常较慢，可通过环境变量加大（秒）
def _read_timeout_sec() -> float:
    raw = os.environ.get("JQ_INDEX_GITHUB_TIMEOUT_SEC", "300").strip()
    try:
        return max(30.0, float(raw))
    except ValueError:
        return 300.0


def _github_client() -> httpx.Client:
    t = _read_timeout_sec()
    return httpx.Client(
        timeout=httpx.Timeout(t, connect=30.0),
        follow_redirects=True,
    )


def _get_with_retries(url: str, *, label: str) -> str:
    """下载 URL 文本；网络抖动时重试。"""
    delays = (1.0, 3.0, 8.0)
    last: Exception | None = None
    for attempt, delay in enumerate(delays):
        try:
            with _github_client() as c:
                r = c.get(url)
                r.raise_for_status()
                return r.text
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.NetworkError, httpx.HTTPError) as e:
            last = e
            if attempt < len(delays) - 1:
                time.sleep(delay)
    raise RuntimeError(
        f"GitHub download failed after retries ({label}): {last}. "
        "If you are in a region where GitHub is slow, use a VPN/proxy, or set "
        f"JQ_INDEX_GITHUB_TIMEOUT_SEC (current read timeout ≈ {_read_timeout_sec():.0f}s) higher, e.g. 600, then retry."
    ) from last

# 核心 API 与财务；alpha/技术分析文件极大，按需 --full 再拉取
DEFAULT_PY_FILES = (
    "__init__.py",
    "api.py",
    "client.py",
    "utils.py",
    "finance_service.py",
    "finance_tables.py",
    "calendar_service.py",
    "table.py",
    "exceptions.py",
    "version.py",
    "thriftclient.py",
)

LARGE_OPTIONAL = (
    "alpha101.py",
    "alpha191.py",
    "technical_analysis.py",
    "fundamentals_tables_gen.py",
)


def list_remote_py_files() -> list[str]:
    text = _get_with_retries(GITHUB_API, label="GitHub API list")
    data = json.loads(text)
    out: list[str] = []
    for item in data:
        if item.get("type") == "file" and str(item.get("name", "")).endswith(".py"):
            out.append(item["name"])
    return sorted(out)


def download_file(filename: str, dest_dir: Path) -> Path:
    url = f"{RAW_BASE}/{filename}"
    dest = dest_dir / filename
    text = _get_with_retries(url, label=filename)
    dest.write_text(text, encoding="utf-8")
    return dest


def download_readme(dest_dir: Path) -> Path | None:
    url = "https://raw.githubusercontent.com/JoinQuant/jqdatasdk/master/README.md"
    dest = dest_dir / "README.md"
    try:
        text = _get_with_retries(url, label="README.md")
        dest.write_text(text, encoding="utf-8")
        return dest
    except (RuntimeError, httpx.HTTPError, OSError):
        return None


def fetch_sources(dest_dir: Path, *, full: bool = False) -> list[Path]:
    """从 GitHub 下载官方仓库源文件到本地缓存目录。"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    files = list(DEFAULT_PY_FILES)
    if full:
        files.extend(LARGE_OPTIONAL)
    written: list[Path] = []
    for name in files:
        written.append(download_file(name, dest_dir))
    rm = download_readme(dest_dir)
    if rm:
        written.append(rm)
    meta = dest_dir / "_fetch_manifest.json"
    meta.write_text(
        json.dumps({"files": [p.name for p in written], "base": RAW_BASE}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return written
