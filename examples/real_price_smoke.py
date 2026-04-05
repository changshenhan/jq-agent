"""
最小示例：用 jqdatasdk 拉取真实行情（需已 pip install jqdatasdk，且账号有数据权限）。

环境变量：
  JQ_PHONE / JQ_PASSWORD — 聚宽账号（与 .env 一致）
  JQ_DATASDK_END_DATE — 可选，YYYY-MM-DD，账号若限制可查询区间时需设为权限内最后交易日

成功时在 stdout 打印一行 BACKTEST_METRICS_JSON，便于 execute_backtest / analyze_backtest_metrics 解析。
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date


def _main() -> None:
    phone = (os.environ.get("JQ_PHONE") or "").strip()
    password = (os.environ.get("JQ_PASSWORD") or "").strip()
    if not phone or not password:
        print("ERROR: 请设置 JQ_PHONE 与 JQ_PASSWORD", file=sys.stderr)
        sys.exit(2)

    try:
        from jqdatasdk import auth, get_price
    except ImportError:
        print("ERROR: pip install jqdatasdk", file=sys.stderr)
        sys.exit(2)

    end_raw = (os.environ.get("JQ_DATASDK_END_DATE") or "").strip()
    end_d = date.fromisoformat(end_raw) if end_raw else date.today()

    try:
        auth(phone, password)
    except Exception as e:
        print(f"ERROR: auth 失败: {e}", file=sys.stderr)
        sys.exit(1)

    security = "000300.XSHG"
    try:
        df = get_price(
            security,
            count=5,
            end_date=end_d,
            frequency="daily",
            fields=["close"],
            skip_paused=True,
            fq="pre",
            panel=False,
        )
    except Exception as e:
        print(f"ERROR: get_price 失败: {e}", file=sys.stderr)
        print("若提示日期权限：请设置 JQ_DATASDK_END_DATE=权限内最后交易日", file=sys.stderr)
        sys.exit(1)

    if df is None or getattr(df, "empty", True):
        print("ERROR: 无行情数据", file=sys.stderr)
        sys.exit(1)

    last = float(df["close"].iloc[-1])
    metrics = {
        "label": "real_price_smoke",
        "security": security,
        "last_close": round(last, 4),
        "bars": int(len(df)),
        "end_date": str(end_d),
        "note": "真实行情快照（非策略回测净值）",
    }
    print("BACKTEST_METRICS_JSON:", json.dumps(metrics, ensure_ascii=False))


if __name__ == "__main__":
    _main()
