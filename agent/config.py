import hashlib
from pathlib import Path
from pydantic_settings import BaseSettings


# Agent's own data directory (always relative to the agent package install location)
_AGENT_HOME = Path.home() / ".agent"


def _detect_project_root() -> Path:
    """Walk up from CWD to find the nearest project root marker."""
    markers = {".git", "pyproject.toml", "package.json", "Cargo.toml", "AGENT.md"}
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if any((parent / m).exists() for m in markers):
            return parent
    return cwd


def _project_session_id(project_root: Path) -> str:
    """Generate a stable session ID from the project path."""
    path_hash = hashlib.sha1(str(project_root).encode()).hexdigest()[:8]
    safe_name = project_root.name.replace(" ", "_")[:20]
    return f"{safe_name}-{path_hash}"


class Config(BaseSettings):
    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    main_model: str = "qwen2.5:7b"
    embed_model: str = "nomic-embed-text"

    # Agent settings
    max_iterations: int = 20
    context_window: int = 8192
    max_history: int = 50
    stream: bool = True

    # Tool settings
    enable_web_search: bool = True
    enable_code_execution: bool = True
    enable_file_tools: bool = True

    # Memory settings
    enable_long_term_memory: bool = True
    memory_top_k: int = 5

    model_config = {"env_file": ".env", "env_prefix": "AGENT_"}


config = Config()

# Project-aware paths (stored globally in ~/.agent, scoped per project)
PROJECT_ROOT = _detect_project_root()
PROJECT_SESSION_ID = _project_session_id(PROJECT_ROOT)

DATA_DIR = _AGENT_HOME / "data"
CHROMA_DIR = _AGENT_HOME / "chroma"
DB_PATH = _AGENT_HOME / "sessions.db"

# Ensure global data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
