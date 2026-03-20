"""
Context compressor: summarizes old conversation history to free up context window.
Called automatically when short-term memory exceeds a threshold.
"""
from agent.utils.logger import log_info


SUMMARY_PROMPT = """以下の会話履歴を簡潔に要約してください。
重要な事実、ユーザーの要求、エージェントの行動と結果を保持してください。
要約は箇条書きで記述し、日本語で回答してください。

会話履歴:
{history}

要約:"""


class ContextCompressor:
    def __init__(self, llm_client):
        self.llm = llm_client

    def compress(self, messages: list[dict], keep_last: int = 10) -> list[dict]:
        """
        Summarize old messages and return a compressed message list.
        Keeps the last `keep_last` messages intact.
        """
        if len(messages) <= keep_last:
            return messages

        to_compress = messages[:-keep_last]
        to_keep = messages[-keep_last:]

        history_text = "\n".join(
            f"{m['role'].upper()}: {m.get('content', '')[:500]}"
            for m in to_compress
            if m.get("content")
        )

        try:
            summary_msg = self.llm.chat(
                messages=[
                    {"role": "user", "content": SUMMARY_PROMPT.format(history=history_text)}
                ],
                stream=False,
            )
            summary = summary_msg.get("content", "").strip()
            log_info(f"Compressed {len(to_compress)} messages into summary.")

            return [
                {"role": "assistant", "content": f"[会話要約]\n{summary}"},
                *to_keep,
            ]
        except Exception as e:
            log_info(f"Compression failed, keeping original history: {e}")
            return messages
