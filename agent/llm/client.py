"""Ollama API client wrapper with streaming and tool-use support."""
from typing import Generator, Optional
import ollama

from agent.config import config
from agent.utils.logger import console, log_error


def _sanitize(text: str) -> str:
    """Remove lone surrogate characters that can't be encoded in UTF-8."""
    return text.encode("utf-8", errors="replace").decode("utf-8")


class LLMClient:
    def __init__(self):
        self.client = ollama.Client(host=config.ollama_host)
        self.model = config.main_model

    def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        stream: bool = False,
    ) -> dict:
        """Send chat request. Returns the assistant message dict."""
        kwargs = dict(model=self.model, messages=messages)
        if tools:
            kwargs["tools"] = tools

        if stream and not tools:
            return self._stream_chat(messages)

        try:
            response = self.client.chat(**kwargs)
            msg = response.message
            # Normalize to plain dict and sanitize content
            return {
                "role": msg.role,
                "content": _sanitize(msg.content or ""),
                "tool_calls": [
                    {
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in (msg.tool_calls or [])
                ],
            }
        except Exception as e:
            log_error(f"LLM error: {_sanitize(str(e))}")
            raise

    def _stream_chat(self, messages: list[dict]) -> dict:
        """Stream response and print tokens in real-time. Returns full message."""
        full_content = ""
        console.print("[bold blue]Assistant:[/bold blue] ", end="")
        try:
            for chunk in self.client.chat(
                model=self.model,
                messages=messages,
                stream=True,
            ):
                token = _sanitize(chunk.message.content or "")
                full_content += token
                console.print(token, end="")
            console.print()  # newline
        except Exception as e:
            console.print()
            log_error(f"Stream error: {_sanitize(str(e))}")
            raise
        return {"role": "assistant", "content": full_content}

    def embed(self, text: str) -> list[float]:
        """Generate embedding vector using the embed model."""
        try:
            response = self.client.embed(
                model=config.embed_model,
                input=text,
            )
            return response.embeddings[0] if response.embeddings else []
        except Exception as e:
            log_error(f"Embedding error: {_sanitize(str(e))}")
            return []

    def close(self) -> None:
        """Close the underlying HTTP connection."""
        try:
            self.client._client.close()
        except Exception:
            pass

    def check_connection(self) -> bool:
        """Verify Ollama is running and model is available."""
        try:
            response = self.client.list()
            # SDK returns ListResponse with .models list of Model objects
            available = [m.model for m in response.models]
            if not any(self.model in m for m in available):
                log_error(
                    f"Model '{self.model}' not found. "
                    f"Run: ollama pull {self.model}"
                )
                return False
            return True
        except Exception as e:
            log_error(f"Cannot connect to Ollama at {config.ollama_host}: {e}")
            return False
