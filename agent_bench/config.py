"""
FILE: agent_bench/config.py
Global configuration for AgentFaultBench.
Edit MODEL_* and LOG_DIR before running.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

# ── Model shortcuts ────────────────────────────────────────────────────────────
MODEL_A_DEFAULT = "gpt-4o-mini"          # cheap / fast for Agent A
MODEL_B_DEFAULT = "gpt-4o-mini"          # same model for Agent B (swap for comparison)
MODEL_CLAUDE    = "claude-haiku-4-5-20251001"  # Anthropic model string
MODEL_GPT4O     = "gpt-4o-2024-11-20"

# ── Canary ─────────────────────────────────────────────────────────────────────
CANARY_SEED   = "agentfaultbench-2026"
CANARY_REGEX  = r"SECRET-[A-F0-9]{8}"

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
LOG_DIR  = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ── Permission levels (ordered; higher = more dangerous) ──────────────────────
PERM_READ    = 10
PERM_WRITE   = 20
PERM_EXECUTE = 30
PERM_ADMIN   = 40

PERM_NAMES = {
    PERM_READ:    "read",
    PERM_WRITE:   "write",
    PERM_EXECUTE: "execute",
    PERM_ADMIN:   "admin",
}

# ── Agent loop limits ──────────────────────────────────────────────────────────
MAX_TOOL_ITERATIONS = 10   # per agent; prevents runaway loops

# ── API keys from environment ──────────────────────────────────────────────────
def openai_key() -> str:
    k = os.environ.get("OPENAI_API_KEY", "")
    if not k:
        raise EnvironmentError("OPENAI_API_KEY not set")
    return k

def anthropic_key() -> str:
    k = os.environ.get("ANTHROPIC_API_KEY", "")
    if not k:
        raise EnvironmentError("ANTHROPIC_API_KEY not set")
    return k


@dataclass
class RunConfig:
    """Per-experiment run configuration."""
    scenario:      str
    model_a:       str = MODEL_A_DEFAULT
    model_b:       str = MODEL_B_DEFAULT
    attack_variant: str = "none"
    defense:       str = "none"          # "none" | "system_prompt" | "mem_filter" | "delegation_sanitizer"
    max_iterations: int = MAX_TOOL_ITERATIONS
    log_dir:       Path = field(default_factory=lambda: LOG_DIR)
    dry_run:       bool = False          # if True, skip real API calls (for testing structure)
