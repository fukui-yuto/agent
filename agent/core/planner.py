"""
Plan-and-Execute: breaks complex tasks into subtasks, then executes each one.
Used automatically for requests that seem multi-step.
"""
import re

from agent.utils.logger import console, log_info, log_warning


PLAN_PROMPT = """あなたはタスクプランナーです。ユーザーのリクエストを分析してください。

【重要ルール】
- 単純な質問や1回のツール呼び出しで解決できる場合は「SIMPLE」とだけ返す
- 複数のステップが必要な場合のみ、番号付きリストで返す
- ステップ数は2〜5個まで
- 各ステップは1行で簡潔に

例（複雑なタスク）:
1. Web検索でPythonの最新バージョンを調べる
2. 調べた情報をまとめて回答する

例（単純なタスク）:
SIMPLE

ユーザーのリクエスト: {request}
"""


REVIEW_PROMPT = """以下のタスクと実行結果を確認してください。

元のリクエスト: {original}
実行したステップと結果:
{results}

全ての重要な情報をまとめて、ユーザーへの最終回答を日本語で作成してください。"""


def _parse_steps(content: str) -> list[str]:
    """Extract numbered steps from LLM response."""
    content = content.strip()

    # If model says SIMPLE, return empty list
    if content.upper().startswith("SIMPLE"):
        return []

    # Extract numbered list items: "1. ...", "2. ..." etc.
    steps = []
    for line in content.splitlines():
        match = re.match(r"^\s*\d+[.)]\s+(.+)", line)
        if match:
            step = match.group(1).strip()
            if step:
                steps.append(step)

    return steps


class Planner:
    def __init__(self, llm_client):
        self.llm = llm_client

    def make_plan(self, request: str) -> list[str]:
        """Ask the LLM to decompose the request into steps."""
        try:
            msg = self.llm.chat(
                messages=[{"role": "user", "content": PLAN_PROMPT.format(request=request)}],
                stream=False,
            )
            content = msg.get("content", "").strip()
            steps = _parse_steps(content)
            return steps
        except Exception as e:
            log_warning(f"Planning failed: {e}")
            return []

    def synthesize(self, original: str, step_results: list[tuple[str, str]]) -> str:
        """Synthesize a final answer from all step results."""
        results_text = "\n".join(
            f"- Step: {step}\n  Result: {result[:500]}"
            for step, result in step_results
        )
        try:
            msg = self.llm.chat(
                messages=[{
                    "role": "user",
                    "content": REVIEW_PROMPT.format(
                        original=original, results=results_text
                    ),
                }],
                stream=False,
            )
            return msg.get("content", "").strip()
        except Exception as e:
            log_warning(f"Synthesis failed: {e}")
            return "\n".join(f"{s}: {r}" for s, r in step_results)
