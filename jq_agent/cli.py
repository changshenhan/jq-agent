from __future__ import annotations

import asyncio
import os

import typer
from rich.console import Console

from jq_agent import __version__
from jq_agent.config import load_settings
from jq_agent.i18n import UiLang, t
from jq_agent.llm.transport import use_http2
from jq_agent.locale_store import load_ui_lang, resolve_ui_lang, save_ui_lang, settings_path
from jq_agent.orchestration.loop import format_stopped_reason, run_agent_loop
from jq_agent.retrieval.linkage import doctor_retrieval_lines
from jq_agent.session_store import list_sessions, session_path, session_tree

app = typer.Typer(
    no_args_is_help=True,
    help="jq-agent — open-source quant Agent framework (JoinQuant-style). Use --lang zh|en for UI language.",
)


@app.callback()
def main_callback(
    ctx: typer.Context,
    lang: str | None = typer.Option(
        None,
        "--lang",
        "-L",
        help="UI language: zh | en (overrides JQ_LANG and ~/.jq-agent/settings.json)",
    ),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["lang"] = resolve_ui_lang(lang, os.environ.get("JQ_LANG"))


@app.command("run")
def run_cmd(
    ctx: typer.Context,
    prompt: str = typer.Argument(..., help="Natural language task / 自然语言任务"),
    model: str | None = typer.Option(None, "--model", "-m", help="Override JQ_MODEL"),
    max_iter: int | None = typer.Option(None, "--max-iter", help="Override max iterations"),
    session: str | None = typer.Option(
        None,
        "--session",
        "-s",
        help="Persist messages to ~/.jq-agent/sessions/<name>.json",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        "-r",
        help="Load prior session before this prompt (needs --session)",
    ),
    stream: bool = typer.Option(
        False,
        "--stream",
        help="Use SSE streaming for LLM (lower time-to-first-token)",
    ),
) -> None:
    """Run agent loop / 运行 Agent 闭环"""
    ui_lang: UiLang = ctx.obj["lang"]
    settings = load_settings()
    if model:
        settings.model = model
    if max_iter is not None:
        settings.max_iterations = max_iter
    if stream:
        settings.llm_stream = True
    console = Console()
    r = asyncio.run(
        run_agent_loop(
            prompt,
            settings,
            console=console,
            ui_lang=ui_lang,
            session_name=session,
            resume_session=resume,
        )
    )
    label = t("stopped", ui_lang)
    suf = t("iterations_suffix", ui_lang)
    detail = format_stopped_reason(r.stopped_reason, ui_lang, settings.max_iterations)
    console.print(f"[bold]{label}:[/bold] {detail}  [dim]({suf}={r.iterations})[/dim]")


@app.command("doctor")
def doctor_cmd(ctx: typer.Context) -> None:
    """Environment check / 环境诊断"""
    ui_lang: UiLang = ctx.obj["lang"]
    s = load_settings()
    c = Console()
    c.print(f"[bold]{t('doctor_title', ui_lang)}[/bold]  [dim]v{__version__}[/dim]")
    c.print(f"{t('doctor_sandbox', ui_lang)}: [cyan]{s.sandbox_dir.resolve()}[/cyan]")
    key_ok = bool(s.llm_api_key.strip())
    ks = t("doctor_key_set", ui_lang) if key_ok else t("doctor_key_unset", ui_lang)
    c.print(f"{t('doctor_key', ui_lang)}: [{'green' if key_ok else 'red'}]{ks}[/{'green' if key_ok else 'red'}]")
    c.print(f"{t('doctor_model', ui_lang)}: {s.model}")
    c.print(f"{t('doctor_base_url', ui_lang)}: {s.llm_base_url}")
    c.print(f"{t('doctor_max_iter', ui_lang)}: {s.max_iterations}")
    c.print(f"LLM stream (JQ_LLM_STREAM): [{'green' if s.llm_stream else 'dim'}]{s.llm_stream}[/]")
    c.print(f"Permission mode (JQ_PERMISSION_MODE): [cyan]{s.permission_mode}[/cyan]")
    c.print(f"Usage log (JQ_USAGE_LOG): {s.usage_log}")
    c.print(f"Session backend (JQ_SESSION_BACKEND): [cyan]{s.session_backend}[/cyan]")
    c.print(f"IDE Agent tools (JQ_IDE_AGENT_TOOLS): [{'green' if s.ide_agent_tools else 'dim'}]{s.ide_agent_tools}[/]")
    c.print(
        f"LLM HTTP/2 (JQ_LLM_HTTP2 + h2): [{'green' if use_http2(s) else 'dim'}]{use_http2(s)}[/]"
    )
    c.print(f"{t('doctor_ui_lang', ui_lang)}: [yellow]{ui_lang}[/yellow]")
    gh_on = "green" if s.github_tools_enabled else "dim"
    c.print(f"{t('doctor_github_tools', ui_lang)}: [{gh_on}]{s.github_tools_enabled}[/]")
    gt = bool(s.github_token.strip())
    c.print(
        f"{t('doctor_github_token', ui_lang)}: [{'green' if gt else 'yellow'}]"
        f"{t('doctor_github_token_yes' if gt else 'doctor_github_token_no', ui_lang)}[/]"
    )
    c.print()
    for line in doctor_retrieval_lines(ui_lang):
        c.print(line)


@app.command("web")
def web_cmd(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address / 监听地址"),
    port: int = typer.Option(8765, "--port", help="Port / 端口"),
) -> None:
    """FastAPI Web UI + SSE log stream / 浏览器界面与流式日志（需 pip install 'jq-agent[web]'）"""
    try:
        import uvicorn
    except ImportError:
        typer.echo("缺少依赖，请执行: pip install 'jq-agent[web]'", err=True)
        raise typer.Exit(code=1) from None
    from jq_agent.web.server import app as web_app

    typer.echo(f"Web UI → http://{host}:{port}/  (health: /health)")
    # httptools +（Unix 上）uvloop 由 uvicorn[standard] 提供；长连接复用略抬高 keep-alive。
    uvicorn.run(
        web_app,
        host=host,
        port=port,
        timeout_keep_alive=120,
    )


config_app = typer.Typer(help="Local preferences / 本地偏好")


def _ctx_lang(ctx: typer.Context) -> UiLang:
    if ctx.parent and getattr(ctx.parent, "obj", None):
        return ctx.parent.obj["lang"]
    return resolve_ui_lang(None, os.environ.get("JQ_LANG"))


@config_app.command("show")
def config_show(ctx: typer.Context) -> None:
    """Show ~/.jq-agent/settings.json / 显示配置文件"""
    ui_lang = _ctx_lang(ctx)
    c = Console()
    c.print(t("config_current", ui_lang, lang=load_ui_lang(), path=str(settings_path())))


@config_app.command("lang")
def config_lang(
    ctx: typer.Context,
    value: str | None = typer.Argument(
        None,
        help="zh | en; omit to print current / 省略则打印当前语言",
    ),
) -> None:
    """Set default UI language (persisted) / 设置默认界面语言（持久化）"""
    ui_lang = _ctx_lang(ctx)
    c = Console()
    if value is None:
        c.print(t("config_current", ui_lang, lang=load_ui_lang(), path=str(settings_path())))
        return
    v = value.strip().lower()
    if v not in ("zh", "en"):
        c.print(f"[red]{t('err_lang_invalid', ui_lang)}[/red]")
        raise typer.Exit(code=1)
    save_ui_lang(v)
    c.print(t("config_saved", ui_lang, lang=v))


app.add_typer(config_app, name="config")

session_app = typer.Typer(help="Session transcripts / 会话落盘")


@session_app.command("list")
def session_list(ctx: typer.Context) -> None:
    """List saved session names under ~/.jq-agent/sessions/"""
    _ = ctx
    names = list_sessions()
    c = Console()
    if not names:
        c.print("[dim]No sessions yet.[/dim]")
        return
    for n in names:
        c.print(f"  • {n}")


@session_app.command("path")
def session_path_cmd(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Session name"),
) -> None:
    """Print filesystem path for a session JSON file"""
    _ = ctx
    Console().print(str(session_path(name)))


@session_app.command("tree")
def session_tree_cmd(ctx: typer.Context) -> None:
    """Show parent/child session rows (SQLite backend only)"""
    _ = ctx
    rows = session_tree()
    c = Console()
    if not rows:
        c.print("[dim]No tree data (use JSON backend or create sessions).[/dim]")
        return
    c.print_json(data=rows)


@app.command("mcp-stdio")
def mcp_stdio_cmd(ctx: typer.Context) -> None:
    """Run MCP server over stdio (requires: pip install 'jq-agent[mcp]')"""
    _ = ctx
    from jq_agent.mcp_stdio import main as mcp_main

    mcp_main()


app.add_typer(session_app, name="session")

index_app = typer.Typer(help="jqdatasdk GitHub → slices → JSON index (+ optional API embeddings) / 官方源码切片与索引")


@index_app.command("build")
def index_build(
    ctx: typer.Context,
    full: bool = typer.Option(
        False,
        "--full",
        "-f",
        help="Also index alpha101 / alpha191 / technical_analysis (large)",
    ),
    no_reset: bool = typer.Option(
        False,
        "--no-reset",
        help="Do not wipe existing index dir before build",
    ),
) -> None:
    """Download JoinQuant/jqdatasdk from GitHub, chunk AST, persist JSON; optional Embeddings API cache."""
    _ = ctx
    c = Console()
    from jq_agent.indexing.vector_build import build_index

    c.print("[bold]Building doc index…[/bold] Slices from GitHub; optional embeddings via your LLM provider API.")
    c.print("[dim]Source: https://github.com/JoinQuant/jqdatasdk (master)[/dim]")
    try:
        meta = build_index(full=full, reset=not no_reset, settings=load_settings())
    except RuntimeError as e:
        c.print(f"[red]{e}[/red]")
        c.print(
            "[dim]若访问 GitHub 较慢：开 VPN/代理，或设置 JQ_INDEX_GITHUB_TIMEOUT_SEC=600 后重试。[/dim]"
        )
        raise typer.Exit(code=1) from e
    if "error" in meta:
        c.print(f"[red]{meta}[/red]")
        raise typer.Exit(code=1)
    c.print(f"[green]OK[/green] chunks={meta['chunk_count']} path={meta.get('index_dir', '')}")


@index_app.command("status")
def index_status_cmd(ctx: typer.Context) -> None:
    """Show index paths, chunk count, and metadata."""
    _ = ctx
    from jq_agent.indexing.vector_build import index_status
    st = index_status()
    cc = Console()
    cc.print_json(data=st)


app.add_typer(index_app, name="index")


if __name__ == "__main__":
    app()
