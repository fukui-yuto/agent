from datetime import datetime
from agent.tools.base import tool


@tool(name="get_datetime", description="Get the current date and time.")
def get_datetime() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")


@tool(name="calculate", description="Evaluate a mathematical expression and return the result.")
def calculate(expression: str) -> str:
    """
    expression: A safe mathematical expression, e.g. '2 ** 10 + 3 * 7'
    """
    allowed = set("0123456789+-*/()., **%")
    if not all(c in allowed for c in expression.replace(" ", "")):
        return "Error: Only basic arithmetic is supported."
    try:
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"Error: {e}"
