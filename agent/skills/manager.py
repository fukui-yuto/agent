"""
Skills system: reusable prompt templates invoked with /skill-name.

Resolution order (higher priority first):
  1. Project-level:  <project>/.skills/*.md
  2. User-level:     ~/.agent/skills/*.md
  3. Built-in:       agent/skills/builtin/*.md
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

from agent.config import PROJECT_ROOT

_AGENT_HOME = Path.home() / ".agent"
_BUILTIN_DIR = Path(__file__).parent / "builtin"


@dataclass
class Skill:
    name: str
    description: str
    prompt: str
    source: str  # "builtin" | "user" | "project"


def _parse_skill(path: Path, source: str) -> Skill | None:
    """Parse a skill markdown file with optional YAML frontmatter."""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None

    # Parse frontmatter: ---\nkey: value\n---
    name = path.stem
    description = ""
    prompt = text

    fm_match = re.match(r"^---\n(.*?)\n---\n?(.*)", text, re.DOTALL)
    if fm_match:
        fm_block, prompt = fm_match.group(1), fm_match.group(2).strip()
        for line in fm_block.splitlines():
            if line.startswith("name:"):
                name = line[5:].strip()
            elif line.startswith("description:"):
                description = line[12:].strip()

    if not prompt:
        return None

    return Skill(name=name, description=description, prompt=prompt, source=source)


class SkillManager:
    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._load()

    def _load(self) -> None:
        """Load skills from all sources (lowest priority first, so higher overwrites)."""
        sources = [
            (_BUILTIN_DIR, "builtin"),
            (_AGENT_HOME / "skills", "user"),
            (PROJECT_ROOT / ".skills", "project"),
        ]
        for directory, source in sources:
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.md")):
                skill = _parse_skill(path, source)
                if skill:
                    self._skills[skill.name] = skill

    def reload(self) -> None:
        self._skills.clear()
        self._load()

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def all(self) -> list[Skill]:
        return sorted(self._skills.values(), key=lambda s: (s.source, s.name))

    def create_user_skill(self, name: str, description: str, prompt: str) -> Path:
        """Save a new skill to the user skills directory."""
        skills_dir = _AGENT_HOME / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        path = skills_dir / f"{name}.md"
        content = f"---\nname: {name}\ndescription: {description}\n---\n{prompt}\n"
        path.write_text(content, encoding="utf-8")
        self.reload()
        return path

    def create_project_skill(self, name: str, description: str, prompt: str) -> Path:
        """Save a new skill to the project .skills directory."""
        skills_dir = PROJECT_ROOT / ".skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        path = skills_dir / f"{name}.md"
        content = f"---\nname: {name}\ndescription: {description}\n---\n{prompt}\n"
        path.write_text(content, encoding="utf-8")
        self.reload()
        return path
