"""
FILE: agent_bench/llm.py
Thin LLM adapter supporting OpenAI-compatible and Anthropic APIs.

Returns a list of tool_calls (dicts) and a text response on each call.
Handles the OpenAI tool-call format and Anthropic's content-block format
uniformly so the Agent class never needs to branch on provider.

AUDIT FIX (critical):
  _call_openai() previously silently dropped the `system` parameter.
  System prompts (role, permission level, instructions) were never sent to
  GPT models. Fixed by prepending a {"role": "system"} message.

PATCH SET 3 — Cross-provider tool-use parity:
  _call_anthropic() now sets tool_choice={"type": "auto"} when tools are
  present, matching OpenAI's tool_choice="auto" behavior.  Without this,
  Anthropic models may default to text-only responses even when tools are
  available, causing false model-parity differences in benchmark results
  (Claude reports UR=0%/ASR=0% while GPT reports UR=100%/ASR=100% on the
  same scenario, purely due to tool invocation rate differences).

PATCH SET 3 — .env loading + fast-fail key validation:
  python-dotenv is used to load a .env file at module init time, so API keys
  do not need to be exported in every shell session.  Both _get_openai() and
  _get_anthropic() now validate that the required key is present before
  constructing the client.  A missing key raises RuntimeError immediately
  rather than sending an empty bearer token, which previously produced a
  confusing 401 error that looked like a model or tool-invocation problem.
  Create a .env file at the project root with:
      OPENAI_API_KEY=sk-...
      ANTHROPIC_API_KEY=sk-ant-...
"""

import os
import json
from typing import Any

# ── .env loading ──────────────────────────────────────────────────────────────
# Part 4: Provider-specific env files (.env.openai / .env.anthropic /
# .env.deepseek) are loaded lazily when the first client for that provider
# is created, so a run that only uses DeepSeek never loads OpenAI keys and
# vice-versa.  The global .env is also loaded once at module init as a
# backward-compatible fallback.
try:
    from dotenv import load_dotenv as _load_dotenv
    from pathlib import Path as _Path

    # Global fallback .env (backward compat — loaded once at import time)
    _load_dotenv(override=False)   # does not overwrite already-set env vars

    def _load_provider_env(provider: str) -> None:
        """
        Try to load .env.<provider> (e.g. .env.openai) from cwd upward.
        Falls through silently if the file does not exist.
        The override=False flag means existing env-var values are never
        overwritten, so CI / Docker secrets remain authoritative.
        """
        candidate = _Path(f".env.{provider}")
        if candidate.exists():
            _load_dotenv(dotenv_path=candidate, override=False)

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

    def _load_provider_env(provider: str) -> None:  # type: ignore[misc]
        pass   # no-op when python-dotenv is absent

    import warnings
    warnings.warn(
        "python-dotenv is not installed; .env files will not be loaded. "
        "Run: pip install python-dotenv",
        stacklevel=1,
    )


# ── Key validation helper ─────────────────────────────────────────────────────

def _require_key(env_var: str, provider: str) -> str:
    """
    Return the value of env_var, or raise a clear RuntimeError.

    Raises early so that a missing key is never sent as an empty bearer
    token.  An empty token produces a provider-side 401 that is easy to
    misdiagnose as a model behaviour or tool-invocation problem.
    """
    key = os.environ.get(env_var)
    if not key:
        raise RuntimeError(
            f"{env_var} not set.  "
            f"Add it to a .env file at the project root or export it before "
            f"running the benchmark:\n"
            f"    echo '{env_var}=your-key-here' >> .env\n"
            f"  or\n"
            f"    export {env_var}=your-key-here\n"
            f"Cannot call {provider} without a valid API key."
        )
    return key


# ── OpenAI ────────────────────────────────────────────────────────────────────
try:
    from openai import OpenAI as _OpenAI
    _openai_client:   "_OpenAI | None" = None
    _deepseek_client: "_OpenAI | None" = None   # Part 3: OpenAI-compat client

    def _get_openai() -> "_OpenAI":
        global _openai_client
        if _openai_client is None:
            _load_provider_env("openai")   # Part 4: load .env.openai if present
            api_key = _require_key("OPENAI_API_KEY", "OpenAI")
            _openai_client = _OpenAI(api_key=api_key)
        return _openai_client

    def _get_deepseek() -> "_OpenAI":
        """
        Part 3: DeepSeek uses an OpenAI-compatible REST API.
        Point the OpenAI client at api.deepseek.com and authenticate with
        DEEPSEEK_API_KEY.  Do NOT use deepseek-reasoner for tool calling —
        use deepseek-chat (the default).
        """
        global _deepseek_client
        if _deepseek_client is None:
            _load_provider_env("deepseek")   # Part 4: load .env.deepseek
            api_key = _require_key("DEEPSEEK_API_KEY", "DeepSeek")
            _deepseek_client = _OpenAI(
                api_key  = api_key,
                base_url = "https://api.deepseek.com",
            )
        return _deepseek_client

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# ── Anthropic ─────────────────────────────────────────────────────────────────
try:
    import anthropic as _anthropic
    _anthropic_client: "_anthropic.Anthropic | None" = None

    def _get_anthropic() -> "_anthropic.Anthropic":
        global _anthropic_client
        if _anthropic_client is None:
            _load_provider_env("anthropic")   # Part 4: load .env.anthropic
            api_key = _require_key("ANTHROPIC_API_KEY", "Anthropic")
            _anthropic_client = _anthropic.Anthropic(api_key=api_key)
        return _anthropic_client

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# ── Unified response type ─────────────────────────────────────────────────────

class LLMResponse:
    """Normalized response from any LLM provider."""

    def __init__(self, text: str, tool_calls: list[dict]):
        self.text       = text          # assistant text (may be empty)
        self.tool_calls = tool_calls    # list of {"name": str, "args": dict, "id": str}

    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    def __repr__(self):
        n = len(self.tool_calls)
        return f"LLMResponse(text={self.text[:60]!r}, tool_calls={n})"


# ── OpenAI-compatible call (shared by OpenAI and DeepSeek) ───────────────────

def _call_openai_compat(
    client: "Any",
    model: str,
    messages: list[dict],
    tools: list[dict],
    system: str = "",
    temperature: float = 0.0,
) -> LLMResponse:
    """
    Core call logic shared by OpenAI and DeepSeek (both use the same wire
    format).  Accepts any OpenAI-compatible client instance.
    """
    full_messages: list[dict] = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    # Some newer OpenAI models (gpt-5-mini, o-series) reject temperature=0.0.
    # Omit the parameter entirely for those models so the API uses its default.
    omit_temp = any(model.startswith(prefix) for prefix in _NO_TEMPERATURE_MODELS)
    kwargs: dict[str, Any] = dict(
        model=model,
        messages=full_messages,
    )
    if not omit_temp:
        kwargs["temperature"] = temperature
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    resp = client.chat.completions.create(**kwargs)
    msg  = resp.choices[0].message
    text = msg.content or ""

    tool_calls: list[dict] = []
    if msg.tool_calls:
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({"name": tc.function.name, "args": args, "id": tc.id})

    return LLMResponse(text=text, tool_calls=tool_calls)


def _call_openai(
    model: str,
    messages: list[dict],
    tools: list[dict],
    system: str = "",           # FIXED: was silently ignored in original
    temperature: float = 0.0,
) -> LLMResponse:
    if not HAS_OPENAI:
        raise ImportError("openai package not installed")
    return _call_openai_compat(
        _get_openai(), model, messages, tools, system, temperature
    )



def _call_deepseek(
    model: str,
    messages: list[dict],
    tools: list[dict],
    system: str = "",
    temperature: float = 0.0,
) -> LLMResponse:
    """
    Part 3: DeepSeek wrapper.  Uses the same OpenAI-compatible call structure
    but routes to api.deepseek.com.
    Default model: deepseek-chat  (NOT deepseek-reasoner — tool calling).
    """
    if not HAS_OPENAI:
        raise ImportError("openai package not installed (required for DeepSeek)")
    return _call_openai_compat(
        _get_deepseek(), model, messages, tools, system, temperature
    )


def _build_openai_tool_result_message(call_id: str, result: str) -> dict:
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": result,
    }


def _build_openai_assistant_with_calls(text: str, tool_calls: list[dict]) -> dict:
    """Build the assistant message that includes tool_call objects."""
    tc_objs = [
        {
            "id": tc["id"],
            "type": "function",
            "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])},
        }
        for tc in tool_calls
    ]
    msg: dict[str, Any] = {"role": "assistant", "content": text or None}
    if tc_objs:
        msg["tool_calls"] = tc_objs
    return msg


# ── Anthropic call ────────────────────────────────────────────────────────────

def _call_anthropic(
    model: str,
    messages: list[dict],
    tools: list[dict],
    system: str = "",
    temperature: float = 0.0,
) -> LLMResponse:
    if not HAS_ANTHROPIC:
        raise ImportError("anthropic package not installed")

    client = _get_anthropic()   # raises RuntimeError if ANTHROPIC_API_KEY missing
    kwargs: dict[str, Any] = dict(
        model=model,
        max_tokens=4096,
        messages=messages,
        temperature=temperature,
    )
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
        # Explicitly request auto tool selection to match OpenAI's
        # tool_choice="auto" behavior.  Anthropic's default without this
        # field is model-dependent and can produce text-only responses even
        # when the task requires a tool call, breaking cross-model parity.
        kwargs["tool_choice"] = {"type": "auto"}

    resp = client.messages.create(**kwargs)

    text       = ""
    tool_calls: list[dict] = []
    for block in resp.content:
        if block.type == "text":
            text += block.text
        elif block.type == "tool_use":
            tool_calls.append({
                "name": block.name,
                "args": block.input or {},
                "id":   block.id,
            })

    return LLMResponse(text=text, tool_calls=tool_calls)


def _build_anthropic_tool_result_message(call_id: str, result: str) -> dict:
    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": call_id,
                "content": result,
            }
        ],
    }


def _build_anthropic_assistant_with_calls(text: str, tool_calls: list[dict]) -> dict:
    content: list[dict] = []
    if text:
        content.append({"type": "text", "text": text})
    for tc in tool_calls:
        content.append({
            "type": "tool_use",
            "id":   tc["id"],
            "name": tc["name"],
            "input": tc["args"],
        })
    return {"role": "assistant", "content": content}


# ── Unified interface ─────────────────────────────────────────────────────────

def _is_anthropic(model: str) -> bool:
    return model.startswith("claude")


def _is_deepseek(model: str) -> bool:
    """Part 3: DeepSeek model names all start with 'deepseek-'."""
    return model.startswith("deepseek")


# Models that reject temperature=0.0 and must be called without the parameter.
# OpenAI reasoning/o-series and newer GPT models (gpt-5-mini, o3, o4-mini, etc.)
# only accept the default temperature (1.0) and return HTTP 400 otherwise.
_NO_TEMPERATURE_MODELS: tuple[str, ...] = (
    "o1", "o2", "o3", "o4",       # o-series prefix match
    "gpt-5",                        # gpt-5 family prefix
)


def llm_call(
    model: str,
    messages: list[dict],
    tools: list[dict],
    system: str = "",
    temperature: float = 0.0,
) -> LLMResponse:
    """Route to the correct provider and return a normalized LLMResponse."""
    if _is_anthropic(model):
        return _call_anthropic(model, messages, tools,
                               system=system, temperature=temperature)
    if _is_deepseek(model):   # Part 3: DeepSeek routing
        return _call_deepseek(model, messages, tools,
                              system=system, temperature=temperature)
    # Default: OpenAI (also handles gpt-4o-mini-2025-08-07 and other new OpenAI IDs)
    return _call_openai(model, messages, tools,
                        system=system, temperature=temperature)


def build_tool_result_message(model: str, call_id: str, result: str) -> dict:
    """Return a provider-appropriate tool-result message dict."""
    if _is_anthropic(model):
        return _build_anthropic_tool_result_message(call_id, result)
    return _build_openai_tool_result_message(call_id, result)


def build_assistant_message(model: str, text: str, tool_calls: list[dict]) -> dict:
    """Return a provider-appropriate assistant message dict (for history)."""
    if _is_anthropic(model):
        return _build_anthropic_assistant_with_calls(text, tool_calls)
    return _build_openai_assistant_with_calls(text, tool_calls)
