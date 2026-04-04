"""
FILE: agent_bench/scenarios/__init__.py
Scenario registry — maps scenario name strings to scenario classes.
"""

from agent_bench.scenarios.memory_poison      import MemoryPoisonScenario
from agent_bench.scenarios.multi_surface      import MultiSurfaceScenario
from agent_bench.scenarios.permission_esc     import PermissionEscScenario
from agent_bench.scenarios.propagation        import PropagationScenario
from agent_bench.scenarios.tool_poison        import ToolPoisonScenario
from agent_bench.scenarios.pdf_injection      import PDFInjectionScenario
from agent_bench.scenarios.audio_injection    import AudioInjectionScenario
from agent_bench.scenarios.cross_modal_relay  import CrossModalRelayScenario

SCENARIO_REGISTRY: dict[str, type] = {
    # ── Original text-surface scenarios ──────────────────────────────────────
    "propagation":        PropagationScenario,
    "memory_poison":      MemoryPoisonScenario,
    "permission_esc":     PermissionEscScenario,
    "tool_poison":        ToolPoisonScenario,
    "multi_surface":      MultiSurfaceScenario,
    # ── Phase 1: PDF surface ──────────────────────────────────────────────────
    "pdf_injection":      PDFInjectionScenario,
    # ── Phase 2: Audio surface ────────────────────────────────────────────────
    "audio_injection":    AudioInjectionScenario,
    # ── Phase 3: Cross-modal relay (highest novelty) ──────────────────────────
    "cross_modal_relay":  CrossModalRelayScenario,
}


def get_scenario(name: str, config):
    """Instantiate and return a scenario by name."""
    cls = SCENARIO_REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown scenario '{name}'. "
            f"Available: {list(SCENARIO_REGISTRY.keys())}"
        )
    return cls(config)
