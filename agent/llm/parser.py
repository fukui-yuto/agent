"""
Parse LLM responses to extract tool calls.
Supports both Ollama native tool-use format and fallback JSON parsing.
"""
import json
import re
from typing import Optional


def parse_tool_call_native(message: dict) -> Optional[tuple[str, dict]]:
    """Extract tool call from Ollama native tool_calls format."""
    tool_calls = message.get("tool_calls")
    if not tool_calls:
        return None
    call = tool_calls[0]
    name = call["function"]["name"]
    args = call["function"].get("arguments", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {}
    return name, args


def parse_tool_call_json(content: str) -> Optional[tuple[str, dict]]:
    """
    Fallback: extract tool call from JSON embedded in text.
    Looks for patterns like:
      {"tool": "name", "args": {...}}
      ```json\n{"tool": ...}\n```
    """
    # Try markdown code block first
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if code_block:
        raw = code_block.group(1)
    else:
        # Try bare JSON object with "tool" key
        raw_match = re.search(r"\{[^{}]*\"tool\"\s*:[^{}]*\}", content, re.DOTALL)
        if not raw_match:
            return None
        raw = raw_match.group(0)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if "tool" not in data:
        return None

    name = data["tool"]
    args = data.get("args", data.get("arguments", data.get("parameters", {})))
    return name, args


def parse_tool_call_from_text(content: str) -> Optional[tuple[str, dict]]:
    """
    Fallback: detect when the model outputs tool invocations as plain text.
    Handles patterns like:
      [Calling write_file]
      ```python
      # filename.py
      ...code...
      ```
    or:
      [Calling run_python]
      ```python
      ...code...
      ```
    """
    call_match = re.search(r"\[Calling (\w+)\]", content)
    if not call_match:
        return None

    tool_name = call_match.group(1)

    # Extract the first code block after the [Calling ...] tag
    after = content[call_match.end():]
    block_match = re.search(r"```(?:\w+)?\s*(.*?)\s*```", after, re.DOTALL)
    if not block_match:
        return None

    code = block_match.group(1).strip()

    if tool_name == "run_python":
        return ("run_python", {"code": code})

    if tool_name == "write_file":
        # Try to find filename from first comment line (# filename.py) or backtick mention
        filename = None
        first_line = code.splitlines()[0] if code else ""
        comment_match = re.match(r"#\s*([\w./-]+\.\w+)", first_line)
        if comment_match:
            filename = comment_match.group(1)
        else:
            name_match = re.search(r"`([\w./-]+\.\w+)`", content)
            if name_match:
                filename = name_match.group(1)
        if not filename:
            filename = "script.py"
        return ("write_file", {"path": filename, "content": code})

    return None


def parse_tool_call(message: dict) -> Optional[tuple[str, dict]]:
    """Try native format, then JSON fallback, then text-pattern fallback."""
    result = parse_tool_call_native(message)
    if result:
        return result
    content = message.get("content", "")
    if content:
        result = parse_tool_call_json(content)
        if result:
            return result
        return parse_tool_call_from_text(content)
    return None
