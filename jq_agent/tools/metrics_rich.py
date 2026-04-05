"""analyze_backtest_metrics 的终端表格展示（Rich）。"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.text import Text


def _fmt_num(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        if abs(v) < 1e6 and v == int(v):
            return str(int(v))
        return f"{float(v):.6g}"
    return str(v)[:80]


def _color_sharpe(v: Any) -> str:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "white"
    if x >= 1.0:
        return "green"
    if x >= 0:
        return "yellow"
    return "red"


def _color_dd(v: Any) -> str:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "white"
    ax = abs(x)
    if ax >= 0.2:
        return "red"
    if ax >= 0.1:
        return "yellow"
    return "green"


def _color_return(v: Any) -> str:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "white"
    if x > 0:
        return "green"
    if x < 0:
        return "red"
    return "white"


def print_metrics_summary(console: Console, tool_json_str: str) -> None:
    """解析 JSON 工具输出，打印彩色指标表（accepted 且含 metrics 时）。"""
    try:
        data = json.loads(tool_json_str)
    except json.JSONDecodeError:
        return
    if not isinstance(data, dict) or not data.get("accepted"):
        return
    metrics = data.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        return

    table = Table(title="回测指标摘要", show_header=True, header_style="bold cyan")
    table.add_column("字段", style="dim", no_wrap=True)
    table.add_column("数值")

    priority_keys = (
        "sharpe_ratio",
        "sharpe",
        "max_drawdown",
        "max_dd",
        "annual_return",
        "total_return",
        "label",
        "security",
        "note",
    )
    shown: set[str] = set()
    for k in priority_keys:
        if k in metrics:
            shown.add(k)
            v = metrics[k]
            style = "white"
            lk = k.lower()
            if "sharpe" in lk:
                style = _color_sharpe(v)
            elif "drawdown" in lk or lk == "max_dd":
                style = _color_dd(v)
            elif "return" in lk:
                style = _color_return(v)
            table.add_row(k, Text(_fmt_num(v), style=style))

    for k, v in sorted(metrics.items()):
        if k in shown:
            continue
        table.add_row(k, Text(_fmt_num(v), style="white"))

    console.print(table)
