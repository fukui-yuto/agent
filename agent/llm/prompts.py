from datetime import datetime
from pathlib import Path


SYSTEM_PROMPT = """You are an autonomous AI assistant with access to tools. You can use tools to help answer questions, perform tasks, and interact with the environment.

Current date/time: {datetime}
Working directory: {cwd}

## Instructions
- Think step by step before taking actions
- Use tools when you need to gather information, execute code, or interact with the system
- After using a tool, analyze the result and decide whether you need more information or can answer
- Be concise and direct in your responses
- If a task requires multiple steps, work through them systematically
- Always provide a final answer to the user after completing your work

{project_instructions}

## Memory context
{memory_context}

## Available tools
You have access to tools for: file operations, code execution, web search, and memory management.
Use them whenever they would help you provide a better answer.
"""


def _load_agent_md(cwd: Path) -> str:
    """Load AGENT.md from the project directory if it exists."""
    agent_md = cwd / "AGENT.md"
    if agent_md.exists():
        content = agent_md.read_text(encoding="utf-8", errors="replace").strip()
        if content:
            return f"## Project instructions (AGENT.md)\n{content}"
    return ""


def build_system_prompt(memory_context: str = "", cwd: Path = None) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cwd = cwd or Path.cwd()

    memory_section = (
        f"Relevant memories from past conversations:\n{memory_context}"
        if memory_context
        else "No relevant memories found."
    )

    project_instructions = _load_agent_md(cwd)

    return SYSTEM_PROMPT.format(
        datetime=now,
        cwd=str(cwd),
        memory_context=memory_section,
        project_instructions=project_instructions,
    )
