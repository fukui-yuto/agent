"""Tools that allow the agent to explicitly manage long-term memory."""
from agent.tools.base import tool

# Will be injected by the orchestrator at runtime
_memory_manager = None


def set_memory_manager(manager) -> None:
    global _memory_manager
    _memory_manager = manager


@tool(name="remember", description="Save important information to long-term memory for future conversations.")
def remember(content: str, category: str = "general") -> str:
    """
    content: The information to remember
    category: Category tag like 'user_preference', 'fact', 'task', etc.
    """
    if _memory_manager is None:
        return "Long-term memory is not available."
    _memory_manager.save(content, category=category)
    return f"Remembered: {content[:100]}"


@tool(name="recall", description="Search long-term memory for relevant information.")
def recall(query: str) -> str:
    """
    query: What to search for in memory
    """
    if _memory_manager is None:
        return "Long-term memory is not available."
    results = _memory_manager.search(query)
    if not results:
        return "No relevant memories found."
    return "\n".join(f"- {r}" for r in results)
