"""
终端外可视化演示：用 Plotly 生成交互 HTML（与 `equity_html` / 主依赖栈一致）。

依赖：已随 jq-agent 安装 plotly、pandas（无需单独 pip matplotlib）。
执行：由 execute_backtest 运行本文件；成功后可用浏览器打开输出的路径。
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def _main() -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("ERROR: pip install plotly", file=sys.stderr)
        sys.exit(2)

    out = Path(__file__).resolve().parent / "demo_equity.html"
    x = list(range(60))
    y = [100.0 + 8 * math.sin(i / 6) + i * 0.12 for i in x]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="Demo equity",
            line=dict(width=2, color="#22c55e"),
            fill="tozeroy",
            fillcolor="rgba(34, 197, 94, 0.15)",
        )
    )
    fig.update_layout(
        title="Demo equity curve (synthetic, not real backtest)",
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=48, r=24, t=56, b=48),
        xaxis_title="day",
        yaxis_title="equity",
    )
    cfg = {"displayModeBar": True, "responsive": True, "scrollZoom": True}
    fig.write_html(str(out), include_plotlyjs="cdn", full_html=True, config=cfg)

    metrics = {
        "note": "plotly demo html written",
        "html_path": str(out),
    }
    print("BACKTEST_METRICS_JSON:", json.dumps(metrics, ensure_ascii=False))
    print(f"OPEN_FILE_HINT: {out}")


if __name__ == "__main__":
    _main()
