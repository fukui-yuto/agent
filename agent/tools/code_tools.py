"""Execute Python code in a subprocess with timeout and basic safety checks."""
import subprocess
import sys
import tempfile
import os
from agent.tools.base import tool

# Dangerous patterns to block
_BLOCKED = [
    "import os", "import sys", "import subprocess", "import shutil",
    "__import__", "open(", "exec(", "eval(", "compile(",
    "os.system", "os.popen", "subprocess.", "shutil.rmtree",
]


def _is_safe(code: str) -> tuple[bool, str]:
    lowered = code.lower()
    for pattern in _BLOCKED:
        if pattern.lower() in lowered:
            return False, f"Blocked: '{pattern}' is not allowed for security reasons."
    return True, ""


@tool(
    name="run_python",
    description="Execute Python code and return stdout/stderr. Imports are restricted for safety.",
)
def run_python(code: str) -> str:
    """
    code: Python code to execute
    """
    safe, reason = _is_safe(code)
    if not safe:
        return reason

    # Write to temp file and execute
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=os.getcwd(),
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (15s limit)."
    except Exception as e:
        return f"Error: {e}"
    finally:
        os.unlink(tmp_path)
