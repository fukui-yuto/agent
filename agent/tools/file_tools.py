import os
from pathlib import Path
from agent.tools.base import tool

# Restrict file access to current working directory
_BASE = Path.cwd()


def _safe_path(path: str) -> Path:
    """Resolve path and ensure it stays within CWD."""
    resolved = (_BASE / path).resolve()
    if not str(resolved).startswith(str(_BASE)):
        raise PermissionError(f"Access denied: '{path}' is outside the working directory.")
    return resolved


@tool(name="read_file", description="Read the contents of a file. Use this before editing a file.")
def read_file(path: str) -> str:
    """
    path: Relative path to the file to read
    """
    p = _safe_path(path)
    if not p.exists():
        return f"Error: File not found: {path}"
    if p.stat().st_size > 1_000_000:
        return "Error: File too large (>1MB). Use a more specific query."
    return p.read_text(encoding="utf-8", errors="replace")


@tool(name="write_file", description="Write content to a file, creating it (and any parent directories) if needed. Always use this tool when asked to create or modify a file.")
def write_file(path: str, content: str) -> str:
    """
    path: Relative path to the file to write
    content: Content to write into the file
    """
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Written {len(content)} characters to {path}"


@tool(name="list_directory", description="List files and directories at a given path.")
def list_directory(path: str = ".") -> str:
    """
    path: Relative directory path to list (defaults to current directory)
    """
    p = _safe_path(path)
    if not p.exists():
        return f"Error: Path not found: {path}"
    if not p.is_dir():
        return f"Error: Not a directory: {path}"

    entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    lines = []
    for e in entries[:100]:
        prefix = "📁 " if e.is_dir() else "📄 "
        lines.append(f"{prefix}{e.name}")
    if len(list(p.iterdir())) > 100:
        lines.append("... (truncated)")
    return "\n".join(lines) if lines else "(empty directory)"


@tool(name="search_files", description="Search for files matching a pattern recursively.")
def search_files(pattern: str, directory: str = ".") -> str:
    """
    pattern: Glob pattern like '*.py' or '**/*.txt'
    directory: Directory to search in (defaults to current directory)
    """
    base = _safe_path(directory)
    matches = list(base.glob(pattern))[:50]
    if not matches:
        return f"No files found matching '{pattern}' in '{directory}'"
    return "\n".join(str(m.relative_to(_BASE)) for m in matches)
