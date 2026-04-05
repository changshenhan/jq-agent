"""
终端外可视化小演示：保存一张 PNG 到脚本同目录（一般为 scratchpad/）。

依赖：pip install matplotlib
执行：由 execute_backtest 运行本文件；成功后用系统图片查看器打开输出的路径。
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def _main() -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("ERROR: pip install matplotlib", file=sys.stderr)
        sys.exit(2)

    out = Path(__file__).resolve().parent / "demo_equity.png"
    x = list(range(60))
    y = [100.0 + 8 * math.sin(i / 6) + i * 0.12 for i in x]

    fig, ax = plt.subplots(figsize=(9, 3))
    ax.plot(x, y, color="#2ecc71", linewidth=1.5)
    ax.fill_between(x, y, alpha=0.15, color="#2ecc71")
    ax.set_title("Demo equity curve (synthetic, not real backtest)")
    ax.set_xlabel("day")
    ax.set_ylabel("equity")
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)

    metrics = {
        "note": "matplotlib demo png written",
        "png_path": str(out),
    }
    print("BACKTEST_METRICS_JSON:", json.dumps(metrics, ensure_ascii=False))
    print(f"OPEN_FILE_HINT: {out}")


if __name__ == "__main__":
    _main()
