"""工具参数 JSON 容错解析（对标 repair 思路的极简实现）。"""

from __future__ import annotations

import ast
import json
import re
from typing import Any


def parse_tool_arguments(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    返回 (args, error)。先标准 json.loads，失败则尝试去 markdown 围栏、截断修复、ast.literal_eval。
    """
    if not raw or not raw.strip():
        return {}, None
    s = raw.strip()
    err: str | None = None
    for attempt in range(3):
        try:
            data = json.loads(s)
            if isinstance(data, dict):
                return data, None
            return {"_value": data}, None
        except json.JSONDecodeError as e:
            err = str(e)
            if attempt == 0:
                s = _strip_markdown_fence(s)
            elif attempt == 1:
                s = _fix_trailing_commas(s)
            else:
                break
    try:
        lit = ast.literal_eval(s)
        if isinstance(lit, dict):
            return lit, None
    except (ValueError, SyntaxError):
        pass
    m = re.search(r"\{[\s\S]*\}\s*$", s)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, dict):
                return data, None
        except json.JSONDecodeError:
            pass
    return None, err or "json_parse_failed"


def _strip_markdown_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return s


def _fix_trailing_commas(s: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", s)
