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


def parse_tool_call(message: dict) -> Optional[tuple[str, dict]]:
    """Try native format first, then fallback to JSON parsing."""
    result = parse_tool_call_native(message)
    if result:
        return result
    content = message.get("content", "")
    if content:
        return parse_tool_call_json(content)
    return None
