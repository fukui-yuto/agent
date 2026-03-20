"""Short-term (in-context) conversation history with rolling window."""
from agent.config import config


class ShortTermMemory:
    def __init__(self):
        self._history: list[dict] = []
        self._max = config.max_history

    def add(self, role: str, content: str) -> None:
        self._history.append({"role": role, "content": content})
        # Rolling window: keep system message (index 0) + last max_history messages
        if len(self._history) > self._max:
            self._history = self._history[-self._max:]

    def add_tool_result(self, tool_name: str, result: str) -> None:
        self._history.append({
            "role": "tool",
            "content": result,
            "name": tool_name,
        })
        if len(self._history) > self._max:
            self._history = self._history[-self._max:]

    def messages(self, system_prompt: str) -> list[dict]:
        """Return full message list with system prompt prepended."""
        return [{"role": "system", "content": system_prompt}] + self._history

    def clear(self) -> None:
        self._history = []

    def __len__(self) -> int:
        return len(self._history)
