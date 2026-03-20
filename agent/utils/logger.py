import sys
import io
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel

theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "tool.name": "bold green",
    "tool.result": "green",
    "llm": "bold blue",
    "user": "bold white",
    "memory": "magenta",
    "dim": "dim",
})

# On Windows, force UTF-8 output so Japanese / emoji characters render correctly
_stdout = sys.stdout
if sys.platform == "win32":
    try:
        _stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
    except Exception:
        pass

console = Console(theme=theme, file=_stdout, highlight=False)


def _safe(msg: str) -> str:
    """Remove lone surrogates so Rich/UTF-8 can encode the string."""
    return msg.encode("utf-8", errors="replace").decode("utf-8")


def log_info(msg: str) -> None:
    console.print(f"[info]i  {_safe(msg)}[/info]")


def log_warning(msg: str) -> None:
    console.print(f"[warning]!  {_safe(msg)}[/warning]")


def log_error(msg: str) -> None:
    console.print(f"[error]ERR  {_safe(msg)}[/error]")


def log_tool_call(name: str, args: dict) -> None:
    args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
    console.print(f"[tool.name]>> {name}[/tool.name][dim]({_safe(args_str)})[/dim]")


def log_tool_result(result: str, truncate: int = 300) -> None:
    display = result[:truncate] + "..." if len(result) > truncate else result
    console.print(f"[tool.result]   -> {_safe(display)}[/tool.result]")


def log_thinking(msg: str) -> None:
    console.print(f"[llm].. {_safe(msg)}[/llm]")


def log_memory(msg: str) -> None:
    console.print(f"[memory][MEM] {_safe(msg)}[/memory]")


def print_separator() -> None:
    console.print("[dim]" + "-" * 60 + "[/dim]")


def print_welcome() -> None:
    console.print(Panel(
        "[bold blue]Ollama Autonomous Agent[/bold blue]\n"
        "[dim]Type your message and press Enter. Type 'exit' or 'quit' to stop.[/dim]\n"
        "[dim]Commands: /clear (clear history), /memory (show memories), /help[/dim]",
        expand=False,
    ))
