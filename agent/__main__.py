"""
Entrypoint for `python -m agent`.
On Windows, automatically re-runs with -X utf8 if needed to ensure
UTF-8 I/O (Ollama SDK uses httpx which requires proper unicode handling).
"""
import sys

if sys.platform == "win32" and sys.flags.utf8_mode == 0:
    import subprocess
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "agent"] + sys.argv[1:]
    )
    sys.exit(result.returncode)

from agent.main import app
app()
