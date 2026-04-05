from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jq_agent.i18n import UiLang, normalize_lang


def settings_path() -> Path:
    d = Path.home() / ".jq-agent"
    d.mkdir(parents=True, exist_ok=True)
    return d / "settings.json"


def load_ui_lang() -> UiLang:
    p = settings_path()
    if not p.exists():
        return "zh"
    try:
        data: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        return normalize_lang(str(data.get("ui_lang", "zh")))
    except (OSError, json.JSONDecodeError, TypeError):
        return "zh"


def save_ui_lang(lang: UiLang | str) -> None:
    lang = normalize_lang(str(lang))
    p = settings_path()
    data: dict[str, Any] = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    data["ui_lang"] = lang
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_ui_lang(cli_lang: str | None, env_lang: str | None) -> UiLang:
    """优先级：CLI --lang > 环境变量 JQ_LANG > ~/.jq-agent/settings.json > zh"""
    if cli_lang:
        return normalize_lang(cli_lang)
    if env_lang and env_lang.strip():
        return normalize_lang(env_lang)
    return load_ui_lang()
