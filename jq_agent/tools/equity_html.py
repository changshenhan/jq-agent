"""回测净值 CSV → Plotly 交互 HTML（scratchpad/backtest_result.html）。"""

from __future__ import annotations

from typing import Any

# 策略在沙箱内写入该 CSV 后，execute_backtest 成功结束时自动生成图表
EQUITY_CSV_REL = "scratchpad/backtest_equity.csv"
HTML_OUT_REL = "scratchpad/backtest_result.html"


def try_generate_equity_html(policy: Any) -> dict[str, Any]:
    """
    若存在 scratchpad/backtest_equity.csv，则生成 scratchpad/backtest_result.html。
    CSV 至少两列：日期列 + 净值列（列名可为 date/equity 或任意前两列）。
    """
    p = policy.ensure_under_sandbox(EQUITY_CSV_REL)
    if not p.exists():
        return {}

    try:
        import pandas as pd
        import plotly.graph_objects as go
    except ImportError as e:
        return {
            "equity_chart_error": f"missing dependency: {e}; pip install plotly pandas",
        }

    try:
        df = pd.read_csv(p)
    except Exception as e:
        return {"equity_chart_error": f"read_csv failed: {e}"}

    if df.empty or len(df.columns) < 2:
        return {"equity_chart_error": "backtest_equity.csv needs at least 2 columns"}

    cols = list(df.columns)
    date_col = next((c for c in cols if str(c).lower() in ("date", "datetime", "time")), cols[0])
    val_col = next(
        (c for c in cols if str(c).lower() in ("equity", "nav", "net_value", "close", "value")),
        cols[1] if cols[1] != date_col else cols[0],
    )
    if val_col == date_col and len(cols) > 1:
        val_col = cols[1]

    x = df[date_col].astype(str)
    y = pd.to_numeric(df[val_col], errors="coerce")
    if y.isna().all():
        return {"equity_chart_error": "equity column is not numeric"}

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="Equity",
            line=dict(width=2, color="#238636"),
            fill="tozeroy",
            fillcolor="rgba(35, 134, 54, 0.12)",
        )
    )
    fig.update_layout(
        title="Equity Curve",
        xaxis_title=str(date_col),
        yaxis_title=str(val_col),
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=48, r=24, t=56, b=48),
    )
    plot_cfg: dict[str, bool | str] = {
        "displayModeBar": True,
        "responsive": True,
        "scrollZoom": True,
    }

    html_path = policy.ensure_under_sandbox(HTML_OUT_REL)
    fig.write_html(
        str(html_path),
        include_plotlyjs="cdn",
        full_html=True,
        config=plot_cfg,
    )

    msg = "回测图表已生成，路径为：.jq-agent/scratchpad/backtest_result.html"
    opened = False
    try:
        import webbrowser

        opened = bool(webbrowser.open(html_path.as_uri()))
    except Exception:
        pass

    out: dict[str, Any] = {
        "equity_chart_html": str(html_path),
        "equity_chart_message": msg,
        "equity_chart_opened_in_browser": opened,
    }
    return out
