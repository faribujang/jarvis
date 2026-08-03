"""
tools/llm.py — the inference provider layer (Layer B) for the Jarvis brain.

Every direct model call made by a TOOL or SKILL (summarize, classify, draft) should
go through llm() so the provider/model is chosen by config, not hardcoded. This keeps
the whole system model-agnostic: switch providers by editing config/providers.yaml,
never by editing code.

    from tools.llm import llm
    text = llm("Summarize this in one sentence: ...")

Smoke test from the repo root (needs a key for the active provider):
    python tools/llm.py "say hi in three words"

Keyless config check (no API call) — prints the active model + whether its key is set,
so you can prove a config/providers.yaml swap changes routing without editing code:
    python tools/llm.py

-----------------------------------------------------------------------------------
STARTER IMPLEMENTATION — Claude Code may update, harden, or restructure this file as
it sees fit (add retries/streaming/async, structured output, message history, better
errors, caching, logging). Keep the public contract stable: a callable `llm(prompt,
model=None) -> str` that resolves its provider/model from config/providers.yaml and
reads API keys from environment variables loaded from .env.
-----------------------------------------------------------------------------------

Dependencies (see tools/requirements.txt): litellm, pyyaml, python-dotenv
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Repo root = parent of this tools/ directory. Used to locate config/ and .env.
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "providers.yaml"


def _load_env() -> None:
    """Load .env from the repo root so API keys are available as env vars."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dependency not installed yet
        return
    load_dotenv(REPO_ROOT / ".env")


def _load_config() -> dict:
    """Read config/providers.yaml and return the active provider's settings."""
    import yaml

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CONFIG_PATH}. Create it (see the starter in config/providers.yaml)."
        )

    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}

    providers = cfg.get("providers", {})
    active = cfg.get("active")
    if not active or active not in providers:
        raise ValueError(
            f"config/providers.yaml: 'active' ({active!r}) is not a key under 'providers'."
        )
    return providers[active]


def llm(prompt: str, model: str | None = None) -> str:
    """
    Send a single prompt to the active (or explicitly named) model and return text.

    Args:
        prompt: the user prompt.
        model:  optional LiteLLM model string to override the config default.

    Returns:
        The model's text response.
    """
    _load_env()
    provider = _load_config()

    resolved_model = model or provider["model"]

    # Ensure the provider's API key env var is present (skip for keyless local models).
    key_env = provider.get("api_key_env")
    if key_env and not os.getenv(key_env):
        raise EnvironmentError(
            f"Environment variable {key_env} is not set. Add it to {REPO_ROOT / '.env'}."
        )

    # Optional passthrough params from config (temperature, max_tokens, api_base, ...).
    extra = {
        k: v
        for k, v in provider.items()
        if k in {"temperature", "max_tokens", "top_p", "api_base"}
    }

    from litellm import completion

    response = completion(
        model=resolved_model,
        messages=[{"role": "user", "content": prompt}],
        **extra,
    )
    return response["choices"][0]["message"]["content"]


def llm_chat(messages: list[dict], model: str | None = None) -> str:
    """
    Send a conversation (list of {"role": ..., "content": ...} dicts) and return text.
    Used by the dashboard chat UI and any multi-turn skill.
    """
    _load_env()
    provider = _load_config()

    resolved_model = model or provider["model"]
    key_env = provider.get("api_key_env")
    if key_env and not os.getenv(key_env):
        raise EnvironmentError(
            f"Environment variable {key_env} is not set. Add it to {REPO_ROOT / '.env'}."
        )

    extra = {
        k: v
        for k, v in provider.items()
        if k in {"temperature", "max_tokens", "top_p", "api_base"}
    }

    from litellm import completion

    response = completion(model=resolved_model, messages=messages, **extra)
    return response["choices"][0]["message"]["content"]


def active_model() -> tuple[str, str | None]:
    """Return (resolved model string, api_key_env) for the active provider — no API call."""
    provider = _load_config()
    return provider["model"], provider.get("api_key_env")


if __name__ == "__main__":
    # No prompt → keyless status check: print the active model + key presence, then exit.
    # Proves config-driven switching — edit `active` in config/providers.yaml, rerun, and
    # this line changes without any code edit. No API call is made, so no key is needed.
    if len(sys.argv) < 2:
        _load_env()
        model, key_env = active_model()
        if key_env:
            status = "set" if os.getenv(key_env) else "MISSING"
            print(f"active model: {model}  (key {key_env}: {status})")
        else:
            print(f"active model: {model}  (no API key required)")
        print('Pass a prompt to run a completion, e.g.  python tools/llm.py "say hi"')
        sys.exit(0)

    print(llm(" ".join(sys.argv[1:])))
