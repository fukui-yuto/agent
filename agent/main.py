"""CLI entry point for the Ollama autonomous agent."""
import sys

# Windows: cp932 locale causes surrogate errors in Ollama SDK responses.
# Re-exec with -X utf8 via python -m agent to force UTF-8 I/O.
# This covers both `python -m agent` (via __main__.py) and `agent.exe` (pipx).
if sys.platform == "win32" and sys.flags.utf8_mode == 0:
    import subprocess
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "agent"] + sys.argv[1:]
    )
    sys.exit(result.returncode)

import typer
from pathlib import Path
from rich.prompt import Prompt

from agent.config import config, PROJECT_ROOT, PROJECT_SESSION_ID
from agent.llm.client import LLMClient
from agent.memory.short_term import ShortTermMemory
from agent.memory.long_term import LongTermMemory
from agent.tools.registry import setup_tools
from agent.tools import memory_tools
from agent.core.orchestrator import Orchestrator
from agent.skills.manager import SkillManager
from agent.utils.logger import (
    console, log_info, log_error,
    print_welcome, print_separator
)

app = typer.Typer(add_completion=False)

_AGENT_MD_TEMPLATE = """\
# Project Instructions

This file is read by the agent every time it starts in this directory.
Write project-specific instructions, conventions, or context here.

## Project overview
(Describe what this project is about)

## Coding conventions
(e.g. language, framework, style guide)

## Important notes
(Anything the agent should always keep in mind)
"""


def _handle_command(
    cmd: str,
    orchestrator: Orchestrator,
    skill_mgr: SkillManager,
) -> bool | None | str:
    """
    Handle slash commands.
    Returns:
      False  — exit signal
      True   — command handled
      str    — skill prompt to execute
      None   — not a recognized command
    """
    raw = cmd.strip()
    cmd_lower = raw.lower()

    if cmd_lower in ("/exit", "/quit"):
        return False

    if cmd_lower == "/clear":
        orchestrator.short_mem.clear()
        log_info("Conversation history cleared.")
        return True

    if cmd_lower == "/memory":
        memories = orchestrator.long_mem.all()
        if not memories:
            log_info("No memories stored yet for this project.")
        else:
            console.print(f"[bold]Project memories ({len(memories)}):[/bold]")
            for i, m in enumerate(memories[:20], 1):
                console.print(f"  {i}. {m[:120]}")
        return True

    if cmd_lower == "/sessions":
        from agent.core.session import SessionManager
        mgr = SessionManager()
        sessions = mgr.list_sessions()
        if not sessions:
            log_info("No saved sessions.")
        else:
            console.print(f"[bold]Saved sessions ({len(sessions)}):[/bold]")
            for s in sessions:
                marker = " <-- current" if s == orchestrator.session_id else ""
                console.print(f"  - {s}{marker}")
        return True

    if cmd_lower == "/init":
        agent_md = PROJECT_ROOT / "AGENT.md"
        if agent_md.exists():
            log_info(f"AGENT.md already exists at {agent_md}")
        else:
            agent_md.write_text(_AGENT_MD_TEMPLATE, encoding="utf-8")
            log_info(f"Created {agent_md} — edit it to add project-specific instructions.")
        return True

    if cmd_lower == "/status":
        agent_md = PROJECT_ROOT / "AGENT.md"
        skills_count = len(skill_mgr.all())
        console.print(f"[bold]Project:[/bold] {PROJECT_ROOT}")
        console.print(f"[bold]Session:[/bold] {orchestrator.session_id}")
        console.print(f"[bold]Model:[/bold]   {config.main_model}")
        console.print(f"[bold]History:[/bold] {len(orchestrator.short_mem)} messages")
        console.print(f"[bold]AGENT.md:[/bold] {'found' if agent_md.exists() else 'not found (run /init)'}")
        console.print(f"[bold]Skills:[/bold]  {skills_count} loaded")
        return True

    # --- Skills commands ---

    if cmd_lower == "/skills":
        skills = skill_mgr.all()
        if not skills:
            log_info("No skills found.")
            return True
        console.print(f"[bold]Available skills ({len(skills)}):[/bold]")
        source_order = ["builtin", "user", "project"]
        current_source = None
        for skill in sorted(skills, key=lambda s: (source_order.index(s.source), s.name)):
            if skill.source != current_source:
                current_source = skill.source
                labels = {"builtin": "Built-in", "user": "User (~/.agent/skills/)", "project": "Project (.skills/)"}
                console.print(f"\n  [dim]{labels[current_source]}[/dim]")
            desc = f" — {skill.description}" if skill.description else ""
            console.print(f"  [bold green]/{skill.name}[/bold green]{desc}")
        console.print()
        return True

    # /skill new <name> — create new user-level skill interactively
    if cmd_lower.startswith("/skill new "):
        name = raw[len("/skill new "):].strip()
        if not name:
            log_error("Usage: /skill new <name>")
            return True
        console.print(f"Creating skill '{name}'. Enter description (or press Enter to skip):")
        try:
            description = input("> ").strip()
            console.print("Enter the skill prompt (type END on a new line to finish):")
            lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            prompt = "\n".join(lines).strip()
            if not prompt:
                log_error("Prompt cannot be empty.")
                return True
            path = skill_mgr.create_user_skill(name, description, prompt)
            log_info(f"Skill '{name}' saved to {path}")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
        return True

    # /skill reload — reload all skills from disk
    if cmd_lower == "/skill reload":
        skill_mgr.reload()
        log_info(f"Skills reloaded ({len(skill_mgr.all())} found).")
        return True

    if cmd_lower == "/help":
        console.print("""
[bold]Commands:[/bold]
  /init          — Create AGENT.md with project-specific instructions
  /status        — Show current project, session, model, and skills info
  /clear         — Clear conversation history (current session)
  /memory        — Show stored long-term memories for this project
  /sessions      — List all saved sessions
  /skills        — List all available skills
  /skill new <name> — Create a new user-level skill interactively
  /skill reload  — Reload skills from disk
  /<skill-name>  — Invoke a skill by name (e.g. /commit, /review)
  /help          — Show this help message
  /exit          — Exit the agent
        """)
        return True

    # --- Skill invocation: /<name> [additional context] ---
    if raw.startswith("/"):
        parts = raw[1:].split(None, 1)
        skill_name = parts[0].lower()
        extra = parts[1] if len(parts) > 1 else ""
        skill = skill_mgr.get(skill_name)
        if skill:
            prompt = skill.prompt
            if extra:
                prompt = f"{prompt}\n\n追加の指示: {extra}"
            log_info(f"Skill '{skill.name}' ({skill.source})")
            return prompt  # Return prompt string to be executed
        # Unknown command
        log_error(f"Unknown command or skill: '{raw}'. Type /help for help.")
        return True

    return None


@app.command()
def main(
    model: str = typer.Option(None, "--model", "-m", help="Ollama model to use"),
    session: str = typer.Option(None, "--session", "-s", help="Session ID (defaults to project-based ID)"),
    no_memory: bool = typer.Option(False, "--no-memory", help="Disable long-term memory"),
    no_web: bool = typer.Option(False, "--no-web", help="Disable web search"),
    no_code: bool = typer.Option(False, "--no-code", help="Disable code execution"),
    no_plan: bool = typer.Option(False, "--no-plan", help="Disable Plan-and-Execute"),
):
    """Ollama Autonomous Agent — run from any project directory."""
    if model:
        config.main_model = model

    session_id = session or PROJECT_SESSION_ID

    print_welcome()
    log_info(f"Project: {PROJECT_ROOT}")
    log_info(f"Model:   {config.main_model} | Session: {session_id}")

    agent_md = PROJECT_ROOT / "AGENT.md"
    if agent_md.exists():
        log_info("AGENT.md found — project instructions loaded.")
    else:
        log_info("No AGENT.md found. Run /init to create one.")

    # Initialize skills
    skill_mgr = SkillManager()
    log_info(f"Skills: {len(skill_mgr.all())} loaded ({[s.name for s in skill_mgr.all()]})")

    # Initialize components
    llm = LLMClient()
    if not llm.check_connection():
        raise typer.Exit(1)

    enable_long_mem = config.enable_long_term_memory and not no_memory
    short_mem = ShortTermMemory()
    long_mem = LongTermMemory(llm_client=llm if enable_long_mem else None)

    registry = setup_tools(
        enable_file=config.enable_file_tools,
        enable_code=config.enable_code_execution and not no_code,
        enable_web=config.enable_web_search and not no_web,
        enable_memory_tools=enable_long_mem,
        enable_system=True,
    )

    memory_tools.set_memory_manager(long_mem)
    print_separator()

    orchestrator = Orchestrator(
        llm, registry, short_mem, long_mem,
        session_id=session_id,
        enable_planner=not no_plan,
    )

    try:
        while True:
            try:
                user_input = Prompt.ask("\n[bold white]You[/bold white]").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Goodbye![/dim]")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                result = _handle_command(user_input, orchestrator, skill_mgr)
                if result is False:
                    console.print("[dim]Goodbye![/dim]")
                    break
                elif isinstance(result, str):
                    # Skill prompt — run through the agent
                    print_separator()
                    try:
                        orchestrator.run(result)
                    except Exception as e:
                        log_error(f"Agent error: {e}")
                    print_separator()
                continue

            if user_input.lower() in ("exit", "quit", "bye"):
                console.print("[dim]Goodbye![/dim]")
                break

            print_separator()
            try:
                orchestrator.run(user_input)
            except Exception as e:
                log_error(f"Agent error: {e}")
            print_separator()
    finally:
        llm.close()


if __name__ == "__main__":
    app()
