"""GitHub REST API 客户端：仅请求 api.github.com，供 Agent 浏览公开仓库与用户主页（结构化数据）。"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx

from jq_agent.config import Settings

GITHUB_API = "https://api.github.com"
USER_AGENT = "jq-agent/1.0.0 (https://github.com/changshenhan/jq-agent)"


def _token(settings: Settings) -> str:
    t = (settings.github_token or "").strip()
    if not t:
        t = (os.environ.get("GITHUB_TOKEN") or "").strip()
    return t


def _headers(settings: Settings) -> dict[str, str]:
    h: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    tok = _token(settings)
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _truncate(s: str | None, max_len: int) -> str:
    if not s:
        return ""
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _request(
    settings: Settings,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{GITHUB_API}{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.request(method, url, headers=_headers(settings), params=params)
    except httpx.RequestError as e:
        return {"error": "github_request_failed", "detail": str(e)}
    try:
        body = r.json() if r.content else {}
    except ValueError:
        body = {"raw": r.text[:2000]}
    if r.status_code >= 400:
        msg = body.get("message") if isinstance(body, dict) else str(body)
        return {
            "error": "github_http_error",
            "status": r.status_code,
            "message": msg,
            "hint": _rate_hint(r.status_code, body),
        }
    if not isinstance(body, dict):
        return {"error": "github_unexpected_response", "detail": str(type(body))}
    return body


def _rate_hint(status: int, body: Any) -> str:
    if status == 403:
        return (
            "可能触发 API 速率限制；可设置 JQ_GITHUB_TOKEN（或 GitHub 标准环境变量 GITHUB_TOKEN）"
            " 以提升匿名 60 次/小时 以上的配额。"
        )
    if status == 404:
        return "资源不存在或无权访问（私有资源需 token 且具备权限）。"
    return ""


def github_search_repositories(
    settings: Settings,
    query: str,
    *,
    sort: str = "best-match",
    order: str = "desc",
    per_page: int = 10,
) -> dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"error": "empty_query", "detail": "q 不能为空"}
    per_page = max(1, min(per_page, 30))
    allowed_sort = {"stars", "forks", "help-wanted-issues", "updated", "best-match"}
    if sort not in allowed_sort:
        sort = "best-match"
    order = "asc" if order.lower() == "asc" else "desc"
    params: dict[str, Any] = {"q": q, "order": order, "per_page": per_page}
    if sort != "best-match":
        params["sort"] = sort
    data = _request(settings, "GET", "/search/repositories", params=params)
    if "error" in data:
        return data
    items_raw = data.get("items")
    if not isinstance(items_raw, list):
        return {"error": "github_bad_shape", "detail": "items 缺失"}
    items: list[dict[str, Any]] = []
    for it in items_raw[:50]:
        if not isinstance(it, dict):
            continue
        items.append(
            {
                "full_name": it.get("full_name"),
                "html_url": it.get("html_url"),
                "description": _truncate(
                    it.get("description") if isinstance(it.get("description"), str) else None,
                    500,
                ),
                "language": it.get("language"),
                "stargazers_count": it.get("stargazers_count"),
                "forks_count": it.get("forks_count"),
                "open_issues_count": it.get("open_issues_count"),
                "updated_at": it.get("updated_at"),
                "default_branch": it.get("default_branch"),
            }
        )
    return {
        "total_count": data.get("total_count"),
        "items": items,
        "notice": "结果来自 GitHub Search API；复杂 query 语法见 https://docs.github.com/search-github/searching-on-github",
    }


def github_search_users(
    settings: Settings,
    query: str,
    *,
    per_page: int = 10,
) -> dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"error": "empty_query", "detail": "q 不能为空"}
    per_page = max(1, min(per_page, 30))
    data = _request(
        settings,
        "GET",
        "/search/users",
        params={"q": q, "per_page": per_page},
    )
    if "error" in data:
        return data
    items_raw = data.get("items")
    if not isinstance(items_raw, list):
        return {"error": "github_bad_shape", "detail": "items 缺失"}
    items: list[dict[str, Any]] = []
    for it in items_raw[:50]:
        if not isinstance(it, dict):
            continue
        items.append(
            {
                "login": it.get("login"),
                "html_url": it.get("html_url"),
                "type": it.get("type"),
            }
        )
    return {
        "total_count": data.get("total_count"),
        "items": items,
        "notice": "用户搜索；获取详情可再调用 github_get_user。",
    }


def github_get_user(settings: Settings, username: str) -> dict[str, Any]:
    u = (username or "").strip().lstrip("@")
    if not u:
        return {"error": "empty_username", "detail": "username 不能为空"}
    if ".." in u or u.count("/") > 0:
        return {"error": "invalid_username", "detail": "非法用户名"}
    data = _request(settings, "GET", f"/users/{quote(u, safe='')}")
    if "error" in data:
        return data
    return {
        "login": data.get("login"),
        "name": data.get("name"),
        "html_url": data.get("html_url"),
        "bio": _truncate(data.get("bio") if isinstance(data.get("bio"), str) else None, 2000),
        "public_repos": data.get("public_repos"),
        "followers": data.get("followers"),
        "following": data.get("following"),
        "created_at": data.get("created_at"),
        "company": data.get("company"),
        "blog": data.get("blog"),
        "location": data.get("location"),
        "twitter_username": data.get("twitter_username"),
    }


def github_get_repository(settings: Settings, owner: str, repo: str) -> dict[str, Any]:
    o = (owner or "").strip()
    r = (repo or "").strip()
    if not o or not r:
        return {"error": "empty_owner_repo", "detail": "owner 与 repo 均不能为空"}
    if ".." in o or ".." in r or "/" in o or "/" in r:
        return {"error": "invalid_owner_repo", "detail": "owner/repo 格式非法"}
    data = _request(
        settings,
        "GET",
        f"/repos/{quote(o, safe='')}/{quote(r, safe='')}",
    )
    if "error" in data:
        return data
    lic = data.get("license") if isinstance(data.get("license"), dict) else {}
    topics = data.get("topics")
    if not isinstance(topics, list):
        topics = []
    return {
        "full_name": data.get("full_name"),
        "html_url": data.get("html_url"),
        "description": _truncate(
            data.get("description") if isinstance(data.get("description"), str) else None,
            2000,
        ),
        "default_branch": data.get("default_branch"),
        "language": data.get("language"),
        "stargazers_count": data.get("stargazers_count"),
        "forks_count": data.get("forks_count"),
        "open_issues_count": data.get("open_issues_count"),
        "updated_at": data.get("updated_at"),
        "pushed_at": data.get("pushed_at"),
        "topics": topics[:20],
        "license": lic.get("spdx_id") if isinstance(lic, dict) else None,
        "archived": data.get("archived"),
        "fork": data.get("fork"),
    }
