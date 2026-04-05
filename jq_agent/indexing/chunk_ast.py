from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocChunk:
    chunk_id: str
    source: str
    text: str
    version: str = "github-master"


def _split_long_text(text: str, max_chars: int = 1500) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def _first_line_unparse(node: ast.AST) -> str:
    if hasattr(ast, "unparse"):
        try:
            full = ast.unparse(node)
            return full.split("\n", 1)[0][:400]
        except Exception:
            pass
    return ""


def extract_chunks_from_py(path: Path, module_hint: str | None = None) -> list[DocChunk]:
    src = path.read_text(encoding="utf-8", errors="replace")
    mod = module_hint or path.stem
    chunks: list[DocChunk] = []

    try:
        tree = ast.parse(src)
    except SyntaxError:
        chunks.append(
            DocChunk(
                chunk_id=f"{mod}::__file__",
                source=str(path.name),
                text=f"# {path.name}\n(语法解析失败，保留片段)\n{src[:4000]}",
            )
        )
        return chunks

    mod_doc = ast.get_docstring(tree)
    if mod_doc and mod_doc.strip():
        text = f"# 模块 {mod}\n\n{mod_doc.strip()}"
        for i, part in enumerate(_split_long_text(text)):
            cid = f"{mod}::__module__" if i == 0 else f"{mod}::__module__p{i}"
            chunks.append(DocChunk(chunk_id=cid, source=path.name, text=part))

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doc = ast.get_docstring(node) or ""
        sig = _first_line_unparse(node)
        if not sig:
            kind = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            sig = f"{kind} {node.name}(...):"
        body = f"{sig}\n\n{doc.strip()}" if doc.strip() else sig
        text = f"## {mod}.{node.name}\n\n{body}"
        for i, part in enumerate(_split_long_text(text)):
            cid = f"{mod}::{node.name}" if i == 0 else f"{mod}::{node.name}_p{i}"
            chunks.append(DocChunk(chunk_id=cid, source=path.name, text=part))

    return chunks


def extract_chunks_from_markdown(path: Path) -> list[DocChunk]:
    text = path.read_text(encoding="utf-8", errors="replace")
    sections = re.split(r"(?m)^##\s+", text)
    out: list[DocChunk] = []
    if len(sections) <= 1:
        out.append(DocChunk(chunk_id="README::__all__", source=path.name, text=text[:8000]))
        return out
    for i, sec in enumerate(sections[1:], start=1):
        lines = sec.split("\n", 1)
        head = lines[0].strip()[:80]
        body = lines[1] if len(lines) > 1 else ""
        out.append(
            DocChunk(
                chunk_id=f"README::s{i}_{head}",
                source=path.name,
                text=f"## {head}\n\n{body.strip()}"[:8000],
            )
        )
    return out


def build_all_chunks(src_dir: Path) -> list[DocChunk]:
    all_c: list[DocChunk] = []
    for p in sorted(src_dir.glob("*.py")):
        if p.name.startswith("_"):
            continue
        all_c.extend(extract_chunks_from_py(p))
    for md in src_dir.glob("*.md"):
        all_c.extend(extract_chunks_from_markdown(md))
    return all_c
