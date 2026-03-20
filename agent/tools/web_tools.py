"""Web search and URL fetching tools."""
import urllib.request
from agent.tools.base import tool


@tool(name="web_search", description="Search the web using DuckDuckGo and return results.")
def web_search(query: str, max_results: int = 5) -> str:
    """
    query: Search query string
    max_results: Number of results to return (default 5)
    """
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}\n   {r['href']}\n   {r['body'][:200]}")
        return "\n\n".join(lines)
    except ImportError:
        return "Error: ddgs not installed. Run: pipenv install ddgs"
    except Exception as e:
        return f"Search error: {e}"


@tool(name="fetch_url", description="Fetch the text content of a URL.")
def fetch_url(url: str) -> str:
    """
    url: Full URL to fetch (must start with http:// or https://)
    """
    if not url.startswith(("http://", "https://")):
        return "Error: URL must start with http:// or https://"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AgentBot/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        # Strip HTML tags if BeautifulSoup is available
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
        except ImportError:
            text = raw

        # Truncate
        if len(text) > 4000:
            text = text[:4000] + "\n... (truncated)"
        return text
    except Exception as e:
        return f"Fetch error: {e}"
