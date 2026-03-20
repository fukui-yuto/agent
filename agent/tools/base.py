"""Tool base class and @tool decorator."""
import inspect
from typing import Any, Callable, get_type_hints
from dataclasses import dataclass, field


# Map Python types to JSON Schema types
_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


@dataclass
class Tool:
    name: str
    description: str
    func: Callable
    parameters: dict = field(default_factory=dict)

    def run(self, **kwargs) -> str:
        try:
            result = self.func(**kwargs)
            return str(result) if result is not None else "Done."
        except Exception as e:
            return f"Error: {e}"

    def to_ollama_schema(self) -> dict:
        """Convert to Ollama tool schema format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def tool(name: str, description: str):
    """Decorator to register a function as a tool with auto-generated JSON schema."""
    def decorator(func: Callable) -> Callable:
        hints = get_type_hints(func)
        sig = inspect.signature(func)

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            py_type = hints.get(param_name, str)
            json_type = _TYPE_MAP.get(py_type, "string")

            # Get description from docstring param section if available
            doc = inspect.getdoc(func) or ""
            param_desc = ""
            for line in doc.splitlines():
                if line.strip().startswith(f"{param_name}:"):
                    param_desc = line.strip()[len(param_name) + 1:].strip()

            properties[param_name] = {"type": json_type, "description": param_desc}

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        parameters = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        func._tool = Tool(
            name=name,
            description=description,
            func=func,
            parameters=parameters,
        )
        return func

    return decorator
