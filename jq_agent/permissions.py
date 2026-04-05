from __future__ import annotations

from pathlib import Path


class PathPolicy:
    """claw/Kilo 式：路径白名单，所有文件与回测必须在沙箱内。"""

    def __init__(self, sandbox_root: Path) -> None:
        self.root = sandbox_root.resolve()

    def ensure_under_sandbox(self, rel_or_abs: str) -> Path:
        p = Path(rel_or_abs)
        if not p.is_absolute():
            p = (self.root / p).resolve()
        else:
            p = p.resolve()
        try:
            p.relative_to(self.root)
        except ValueError as e:
            raise PermissionError(
                f"path outside sandbox: {p} (sandbox root={self.root})"
            ) from e
        return p

    def mkdir(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
