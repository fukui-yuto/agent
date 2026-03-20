"""
Core ReAct loop orchestrator.
Thought → Action (tool call) → Observation → ... → Answer

Integrates:
- Short-term memory with auto-compression
- Long-term memory (ChromaDB)
- Tool execution
- Plan-and-Execute for multi-step tasks
- Session persistence (SQLite)
"""
from agent.config import config, PROJECT_ROOT
from agent.llm.client import LLMClient
from agent.llm.parser import parse_tool_call
from agent.llm.prompts import build_system_prompt
from agent.memory.short_term import ShortTermMemory
from agent.memory.long_term import LongTermMemory
from agent.memory.compressor import ContextCompressor
from agent.core.planner import Planner
from agent.core.session import SessionManager
from agent.tools.registry import ToolRegistry
from agent.utils.logger import (
    console, log_tool_call, log_tool_result, log_error, log_warning, log_info
)

# Threshold: compress history when exceeding this many messages
_COMPRESS_THRESHOLD = 30


class Orchestrator:
    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        short_mem: ShortTermMemory,
        long_mem: LongTermMemory,
        session_id: str = "default",
        enable_planner: bool = True,
    ):
        self.llm = llm
        self.registry = registry
        self.short_mem = short_mem
        self.long_mem = long_mem
        self.session_id = session_id
        self.compressor = ContextCompressor(llm)
        self.planner = Planner(llm) if enable_planner else None
        self.session_mgr = SessionManager()

        # Restore previous session if available
        self._restore_session()

    def _restore_session(self) -> None:
        messages = self.session_mgr.load(self.session_id)
        if messages:
            for msg in messages:
                self.short_mem.add(msg["role"], msg["content"])
            log_info(f"Session '{self.session_id}' restored ({len(messages)} messages)")

    def _save_session(self) -> None:
        self.session_mgr.save(self.session_id, self.short_mem._history)

    def _maybe_compress(self) -> None:
        if len(self.short_mem) >= _COMPRESS_THRESHOLD:
            log_info("Compressing conversation history...")
            compressed = self.compressor.compress(
                self.short_mem._history, keep_last=10
            )
            self.short_mem._history = compressed

    def _react_loop(self, user_input: str, system_prompt: str) -> str:
        """Core ReAct loop. Returns the final text response."""
        tool_schemas = self.registry.schemas()
        final_response = ""

        for step in range(config.max_iterations):
            messages = self.short_mem.messages(system_prompt)
            message = self.llm.chat(messages, tools=tool_schemas, stream=False)

            tool_call = parse_tool_call(message)

            if tool_call:
                tool_name, tool_args = tool_call
                log_tool_call(tool_name, tool_args)
                result = self.registry.execute(tool_name, tool_args)
                log_tool_result(result)

                self.short_mem.add(
                    "assistant",
                    message.get("content") or f"[Calling {tool_name}]"
                )
                self.short_mem.add_tool_result(tool_name, result)

            else:
                content = message.get("content", "").strip()
                if not content:
                    log_warning("Empty response from LLM.")
                    content = "応答を生成できませんでした。もう一度お試しください。"

                console.print("[bold blue]Assistant:[/bold blue] ", end="")
                console.print(content, highlight=False)

                self.short_mem.add("assistant", content)
                final_response = content
                break
        else:
            log_warning(f"Reached max iterations ({config.max_iterations}).")
            final_response = "最大ステップ数に達しました。リクエストを簡単にしてお試しください。"
            self.short_mem.add("assistant", final_response)

        return final_response

    def run(self, user_input: str) -> str:
        """Process user input and return final response."""
        # Auto-compress if history is too long
        self._maybe_compress()

        # Retrieve relevant long-term memories
        memory_context = ""
        if self.long_mem.available:
            memories = self.long_mem.search(user_input)
            if memories:
                memory_context = "\n".join(f"- {m}" for m in memories)

        system_prompt = build_system_prompt(memory_context, cwd=PROJECT_ROOT)

        # --- Plan-and-Execute for complex multi-step tasks ---
        final_response = ""
        if self.planner:
            steps = self.planner.make_plan(user_input)
            if len(steps) >= 2:
                log_info(f"Plan ({len(steps)} steps): " + " → ".join(steps))
                step_results = []
                for i, step in enumerate(steps, 1):
                    console.print(f"[dim]Step {i}/{len(steps)}: {step}[/dim]")
                    self.short_mem.add("user", step)
                    result = self._react_loop(step, system_prompt)
                    step_results.append((step, result))

                # Synthesize final answer from all step results
                final_response = self.planner.synthesize(user_input, step_results)
                console.print("[bold blue]Assistant (summary):[/bold blue] ", end="")
                console.print(final_response, highlight=False)
                self.short_mem.add("assistant", final_response)
            else:
                # Simple request — standard ReAct loop
                self.short_mem.add("user", user_input)
                final_response = self._react_loop(user_input, system_prompt)
        else:
            self.short_mem.add("user", user_input)
            final_response = self._react_loop(user_input, system_prompt)

        # Auto-save to long-term memory
        if self.long_mem.available and len(user_input) > 20:
            self.long_mem.save(
                f"User: {user_input[:200]} | Answer: {final_response[:200]}",
                category="conversation",
            )

        # Persist session
        self._save_session()

        return final_response
