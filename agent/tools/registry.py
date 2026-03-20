"""Central tool registry: register, list, and execute tools."""
from agent.tools.base import Tool
from agent.utils.logger import log_error


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def register_module(self, module) -> None:
        """Auto-register all @tool-decorated functions in a module."""
        import inspect
        for _, obj in inspect.getmembers(module, inspect.isfunction):
            if hasattr(obj, "_tool"):
                self.register(obj._tool)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def schemas(self) -> list[dict]:
        """Return all tool schemas in Ollama format."""
        return [t.to_ollama_schema() for t in self._tools.values()]

    def execute(self, name: str, args: dict) -> str:
        tool = self.get(name)
        if not tool:
            return f"Unknown tool: '{name}'. Available: {list(self._tools.keys())}"
        return tool.run(**args)


# Global registry instance
registry = ToolRegistry()


def setup_tools(
    enable_file: bool = True,
    enable_code: bool = True,
    enable_web: bool = True,
    enable_memory_tools: bool = True,
    enable_system: bool = True,
) -> ToolRegistry:
    """Import and register all tool modules based on config."""
    if enable_system:
        from agent.tools import system_tools
        registry.register_module(system_tools)

    if enable_file:
        from agent.tools import file_tools
        registry.register_module(file_tools)

    if enable_code:
        from agent.tools import code_tools
        registry.register_module(code_tools)

    if enable_web:
        from agent.tools import web_tools
        registry.register_module(web_tools)

    if enable_memory_tools:
        from agent.tools import memory_tools
        registry.register_module(memory_tools)

    return registry
