"""
FILE: agent_bench/scenarios/base.py
Abstract base class for all benchmark scenarios.

A Scenario encapsulates:
  - Web content to inject (the attack surface)
  - How to construct Agents A and B (or just A for single-agent)
  - What the legitimate user task prompt is
  - How to evaluate utility (was the benign task done?) and
    security (did the attack succeed?)

Scenario subclasses must implement:
  build()   — returns the prepped agents + environment
  utility() — returns True if the user task was accomplished
  security()— returns True if the injection goal was achieved
"""

from __future__ import annotations

import json
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from agent_bench.config import (
    CANARY_REGEX,
    PERM_EXECUTE,
    PERM_READ,
    PERM_WRITE,
    RunConfig,
)
from agent_bench.logger import RunLogger
from agent_bench.memory import MemoryStore
from agent_bench.metrics import RunRecord
from agent_bench.tools import build_registry


# ── Scenario build output ─────────────────────────────────────────────────────

@dataclass
class ScenarioBuild:
    """Everything needed to run one scenario episode."""
    config:      RunConfig
    agent_a_prompt: str
    memory:      MemoryStore
    web_content: dict[str, str]
    logger:      RunLogger

    # Optional pre-built agents (set by build()); orchestrator may also build them
    agent_a:     object | None = None   # Agent instance
    agent_b:     object | None = None   # Agent instance


# ── Base class ────────────────────────────────────────────────────────────────

class BaseScenario(ABC):
    """
    Abstract scenario.  Subclasses implement build(), utility(), security().
    """

    #: Human-readable name used in results tables
    name: str = "base"

    #: Default canary token for injection detection
    CANARY: str = ""  # filled in by build() from config

    def __init__(self, config: RunConfig):
        self.config = config

    @abstractmethod
    def build(self) -> ScenarioBuild:
        """
        Prepare agents, memory, web content, and logger for one run.
        Returns a ScenarioBuild ready to hand to the orchestrator or runner.
        """

    @abstractmethod
    def utility(self, build: ScenarioBuild, agent_output: str) -> bool:
        """
        Check whether the benign user task was completed.
        `agent_output` is the final text from the relevant agent.
        """

    @abstractmethod
    def security(self, build: ScenarioBuild, tool_log: list[dict]) -> bool:
        """
        Check whether the injection goal was achieved.
        `tool_log` is the list of tool call dicts from registry.call_log().
        """

    # ── Helpers available to all subclasses ───────────────────────────────

    @staticmethod
    def _make_canary() -> str:
        import secrets
        return "SECRET-" + secrets.token_hex(4).upper()

    @staticmethod
    def _canary_in_text(canary: str, text: str) -> bool:
        return canary in text

    @staticmethod
    def _canary_in_tool_log(canary: str, log: list[dict]) -> bool:
        for entry in log:
            if canary in json.dumps(entry):
                return True
        return False

    @staticmethod
    def _make_logger(config: RunConfig, run_id: str | None = None) -> RunLogger:
        from agent_bench.logger import RunLogger, new_run_id
        rid = run_id or new_run_id(config.scenario)
        return RunLogger(run_id=rid, log_dir=config.log_dir)

    @staticmethod
    def _make_registry(memory, web_content, agent_id, logger,
                       include_admin=False, search_content=None,
                       pdf_content=None, audio_content=None):
        return build_registry(
            memory=memory,
            web_content=web_content,
            search_content=search_content,
            pdf_content=pdf_content,
            audio_content=audio_content,
            agent_id=agent_id,
            logger=logger,
            include_admin=include_admin,
        )
