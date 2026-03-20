"""
Plan-and-Execute: breaks complex tasks into subtasks, then executes each one.
Used automatically for requests that seem multi-step.
"""
import re

from agent.utils.logger import console, log_info, log_warning


PLAN_PROMPT = """あなたはAIエージェントのタスクプランナーです。ユーザーのリクエストを分析し、エージェント自身がツールを使って実行するステップに分解してください。

【重要ルール】
- 単純な質問や1回のツール呼び出しで解決できる場合は「SIMPLE」とだけ返す
- 複数のステップが必要な場合のみ、番号付きリストで返す
- ステップ数は2〜5個まで
- 各ステップは「エージェントが何をするか」を書く（ユーザーへの手順説明ではない）
- 「エディタを開く」「コピーして貼り付ける」など人間の手作業ステップは書かない

例（ファイル作成タスク）:
1. Pythonスクリプトの内容を考えてファイルに保存する
2. 作成したファイルの内容を確認して報告する

例（調査タスク）:
1. 必要な情報をWeb検索で収集する
2. 収集した情報をまとめて回答する

例（単純なタスク）:
SIMPLE

ユーザーのリクエスト: {request}
"""


REVIEW_PROMPT = """以下のタスクと実行結果を確認してください。

元のリクエスト: {original}
実行したステップと結果:
{results}

【重要】エージェントが実際に実行した結果をまとめてください。ユーザーへの手順説明や「〜してください」という指示は不要です。何を作成・実行・取得したかを簡潔に日本語で報告してください。"""


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
