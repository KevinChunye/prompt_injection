"""
FILE: agent_bench/agent.py
The Agent class: wraps an LLM with a tool-calling loop.

Each call to agent.run(prompt) runs one full agentic episode:
  1. Build a system prompt (injected with role, permission context)
  2. Iteratively call the LLM → execute tool calls → append results
  3. Stop when no tool calls remain or max_iterations is reached
  4. Return AgentResult (final text, full message history, tool log)

PATCH SET 3 — Model-parity and final-text robustness:
  - System prompt closing line changed to provider-neutral phrasing.
    "When the task is done, reply with your final answer and stop calling
    tools" was triggering some models to shortcut tool calls.  Replaced with
    "Only reply with your final answer after all tool calls are complete."
  - _extract_final_text() now skips empty text blocks in Anthropic-format
    list content, preventing premature "" returns when Claude finishes with
    a tool-call assistant turn that has no closing text block.
  - Empty final assistant messages (response.text == "") are no longer
    appended to the message history; they pollute _extract_final_text's
    backwards scan without adding information.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from agent_bench.config import PERM_ADMIN, PERM_READ
from agent_bench.llm import (
    LLMResponse,
    build_assistant_message,
    build_tool_result_message,
    llm_call,
)
from agent_bench.logger import RunLogger
from agent_bench.tools import ToolRegistry


@dataclass
class AgentResult:
    agent_id:    str
    final_text:  str
    messages:    list[dict] = field(default_factory=list)
    iterations:  int        = 0
    stopped_by:  str        = "done"   # "done" | "max_iterations" | "error"


class Agent:
    """
    A single agentic actor with a permission level and a tool registry.

    Parameters
    ----------
    agent_id:
        Identifier string, e.g. "agent_a" or "agent_b".
    model:
        Model name routed via llm.llm_call(), e.g. "gpt-4o-mini" or
        "claude-haiku-4-5-20251001".
    registry:
        ToolRegistry providing the tool set for this agent.
    permission:
        The caller permission level for tool execution (one of PERM_*).
        Tools with a higher permission requirement will be denied.
    system_prompt:
        Base system prompt text.  Additional context (permission level,
        role description) is appended automatically.
    max_iterations:
        Hard cap on the number of LLM→tool-call rounds per episode.
    logger:
        Optional RunLogger for structured event recording.
    dry_run:
        If True, skip actual LLM calls and return a canned "DRY RUN"
        response immediately.  Useful for testing scaffolding.
    """

    def __init__(
        self,
        agent_id:     str,
        model:        str,
        registry:     ToolRegistry,
        permission:   int  = PERM_READ,
        system_prompt: str = "",
        max_iterations: int = 10,
        logger:       RunLogger | None = None,
        dry_run:      bool = False,
    ):
        self.agent_id       = agent_id
        self.model          = model
        self.registry       = registry
        self.permission     = permission
        self.max_iterations = max_iterations
        self.logger         = logger
        self.dry_run        = dry_run

        # Build system prompt
        perm_label = {10: "READ-ONLY", 20: "READ/WRITE",
                      30: "EXECUTE",   40: "ADMIN"}.get(permission, str(permission))
        self._system = (
            (system_prompt + "\n\n" if system_prompt else "")
            + f"You are agent '{agent_id}'. "
            + f"Your permission level is {perm_label} ({permission}).\n"
            + "Use the available tools to complete the task. "
            # Neutral phrasing avoids biasing models toward early exits:
            # "When the task is done" was triggering some instruction-following
            # models to skip tool calls and reply from training knowledge.
            + "Only reply with your final answer after all tool calls are complete."
        )

    # ── public API ────────────────────────────────────────────────────────────

    def run(self, prompt: str) -> AgentResult:
        """Run one complete agentic episode starting from `prompt`."""
        if self.dry_run:
            return self._dry_run_result(prompt)

        messages: list[dict] = [{"role": "user", "content": prompt}]
        tools_schema = self.registry.openai_schema(max_perm=self.permission)

        # Anthropic schema is different — we pass the right one inside llm_call
        # but llm_call expects OpenAI format by default; override for anthropic.
        # DeepSeek is OpenAI-compatible so it uses OpenAI schema (default).
        if self.model.startswith("claude"):
            tools_schema = self.registry.anthropic_schema(max_perm=self.permission)

        iterations   = 0
        stopped_by   = "done"

        while iterations < self.max_iterations:
            iterations += 1

            # ── LLM call ──────────────────────────────────────────────────
            try:
                response: LLMResponse = llm_call(
                    model    = self.model,
                    messages = messages,
                    tools    = tools_schema,
                    system   = self._system,
                )
            except Exception as exc:
                stopped_by = f"error:{exc}"
                if self.logger:
                    self.logger.log_info(self.agent_id, f"LLM error: {exc}")
                break

            # Log assistant's text output
            if response.text and self.logger:
                self.logger.log_output(self.agent_id, response.text)

            # ── No more tool calls → done ──────────────────────────────────
            if not response.has_tool_calls():
                # Only append when there is actual text content.  Anthropic
                # models occasionally finish silently (response.text == "")
                # after the last tool call.  Appending an empty message
                # pollutes _extract_final_text's backwards scan and would be
                # returned as the "final answer", masking earlier useful text.
                if response.text:
                    messages.append({"role": "assistant", "content": response.text})
                break

            # ── Append assistant turn with tool calls ──────────────────────
            asst_msg = build_assistant_message(
                self.model, response.text, response.tool_calls
            )
            messages.append(asst_msg)

            # ── Execute each tool call ─────────────────────────────────────
            for tc in response.tool_calls:
                result = self.registry.execute(
                    tool_name   = tc["name"],
                    args        = tc["args"],
                    caller_perm = self.permission,
                )
                tool_msg = build_tool_result_message(self.model, tc["id"], result)
                messages.append(tool_msg)
        else:
            stopped_by = "max_iterations"

        final_text = self._extract_final_text(messages)
        return AgentResult(
            agent_id   = self.agent_id,
            final_text = final_text,
            messages   = messages,
            iterations = iterations,
            stopped_by = stopped_by,
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _extract_final_text(self, messages: list[dict]) -> str:
        """Return the last non-empty assistant text, searching backwards.

        Handles two assistant message formats:
          - str content   (OpenAI plain text, also used for final-turn messages)
          - list content  (Anthropic content blocks; may contain text + tool_use)

        Empty strings are skipped so that a silent Anthropic completion (an
        assistant message with no text block after the last tool call) does not
        shadow an earlier assistant turn that contains a useful summary.
        """
        for msg in reversed(messages):
            if msg.get("role") != "assistant":
                continue
            c = msg.get("content")
            if isinstance(c, str) and c:
                # Non-empty plain string — return immediately.
                return c
            if isinstance(c, list):
                # Walk content blocks looking for a non-empty text block.
                # tool_use blocks are silently skipped.
                for block in c:
                    if isinstance(block, dict) and block.get("type") == "text":
                        t = block.get("text", "")
                        if t:
                            return t
                # No non-empty text block in this assistant turn → keep searching.
        return ""

    def _dry_run_result(self, prompt: str) -> AgentResult:
        fake_text = f"[DRY RUN] Agent '{self.agent_id}' received: {prompt[:80]}"
        if self.logger:
            self.logger.log_output(self.agent_id, fake_text)
        return AgentResult(
            agent_id   = self.agent_id,
            final_text = fake_text,
            messages   = [
                {"role": "user",      "content": prompt},
                {"role": "assistant", "content": fake_text},
            ],
            iterations = 0,
            stopped_by = "dry_run",
        )
