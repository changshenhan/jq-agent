"""策略文件静态检查：可选调用 ruff（无则跳过）。"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_ruff_check(file_path: Path, *, timeout_sec: float = 60.0) -> dict[str, Any]:
    exe = shutil.which("ruff")
    if not exe:
        return {"skipped": True, "reason": "ruff_not_on_path", "hint": "pip install ruff"}
    try:
        proc = subprocess.run(
            [exe, "check", str(file_path), "--output-format", "full"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        return {
            "skipped": False,
            "exit_code": proc.returncode,
            "stdout": (proc.stdout or "")[-12000:],
            "stderr": (proc.stderr or "")[-4000:],
        }
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"skipped": False, "error": str(e), "python": sys.executable}
