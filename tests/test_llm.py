"""
Unit tests for tools/llm.py — the Layer B provider wrapper.

NO REAL MODEL CALLS. A fake `litellm` module is injected into sys.modules, so these
tests never hit the network and never need an API key. They verify config-driven
routing, the key-presence guard, param passthrough, and the llm() contract.

Run from the repo root:
    python -m unittest discover -s tests -v

Requires: pyyaml (in tools/requirements.txt). No other setup, no .env, no key.
"""

import os
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import llm as llmmod  # noqa: E402


class FakeCompletion:
    """Records calls and returns a canned OpenAI-style response — no network."""

    def __init__(self, content="canned response"):
        self.content = content
        self.calls = []

    def completion(self, **kwargs):
        self.calls.append(kwargs)
        return {"choices": [{"message": {"content": self.content}}]}


class LlmTestBase(unittest.TestCase):
    def setUp(self):
        # Isolate: never read a real .env, never inherit a real key.
        self._orig_load_env = llmmod._load_env
        self._orig_config_path = llmmod.CONFIG_PATH
        self._orig_key = os.environ.pop("GEMINI_API_KEY", None)
        llmmod._load_env = lambda: None  # no-op

        # Inject a fake litellm so `from litellm import completion` picks up our stub.
        self.fake = FakeCompletion()
        fake_mod = types.ModuleType("litellm")
        fake_mod.completion = self.fake.completion
        self._orig_litellm = sys.modules.get("litellm")
        sys.modules["litellm"] = fake_mod

    def tearDown(self):
        llmmod._load_env = self._orig_load_env
        llmmod.CONFIG_PATH = self._orig_config_path
        if self._orig_key is not None:
            os.environ["GEMINI_API_KEY"] = self._orig_key
        else:
            os.environ.pop("GEMINI_API_KEY", None)
        if self._orig_litellm is not None:
            sys.modules["litellm"] = self._orig_litellm
        else:
            sys.modules.pop("litellm", None)

    def _write_config(self, text: str) -> None:
        """Point llm.py at a temporary providers.yaml for this test."""
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        cfg = Path(self._tmp.name) / "providers.yaml"
        cfg.write_text(text, encoding="utf-8")
        llmmod.CONFIG_PATH = cfg


class TestRealConfig(LlmTestBase):
    """Tests against the actual config/providers.yaml shipped in the repo."""

    def test_active_model_is_gemini_flash(self):
        model, key_env = llmmod.active_model()
        self.assertEqual(model, "gemini/gemini-2.5-flash")
        self.assertEqual(key_env, "GEMINI_API_KEY")

    def test_missing_key_raises_before_any_call(self):
        with self.assertRaises(EnvironmentError):
            llmmod.llm("hello")
        # Critical: the guard fires BEFORE any completion call is made.
        self.assertEqual(self.fake.calls, [])

    def test_llm_returns_content_and_routes_to_active_model(self):
        os.environ["GEMINI_API_KEY"] = "test-key-not-real"
        out = llmmod.llm("hello")
        self.assertEqual(out, "canned response")
        self.assertEqual(len(self.fake.calls), 1)
        call = self.fake.calls[0]
        self.assertEqual(call["model"], "gemini/gemini-2.5-flash")
        self.assertEqual(call["messages"], [{"role": "user", "content": "hello"}])

    def test_model_override_wins(self):
        os.environ["GEMINI_API_KEY"] = "test-key-not-real"
        llmmod.llm("hi", model="gemini/gemini-2.5-pro")
        self.assertEqual(self.fake.calls[0]["model"], "gemini/gemini-2.5-pro")


class TestConfigSwitching(LlmTestBase):
    """Config-driven switching: editing YAML changes routing with no code edit."""

    def test_swap_to_keyless_ollama(self):
        self._write_config(
            "active: local\n"
            "providers:\n"
            "  local:\n"
            "    model: ollama/qwen2.5\n"
            "    api_base: http://localhost:11434\n"
        )
        model, key_env = llmmod.active_model()
        self.assertEqual(model, "ollama/qwen2.5")
        self.assertIsNone(key_env)  # keyless
        # No key set, yet the call goes through (keyless provider).
        out = llmmod.llm("hi")
        self.assertEqual(out, "canned response")
        self.assertEqual(self.fake.calls[0]["model"], "ollama/qwen2.5")

    def test_passthrough_params_forwarded(self):
        self._write_config(
            "active: local\n"
            "providers:\n"
            "  local:\n"
            "    model: ollama/qwen2.5\n"
            "    temperature: 0.1\n"
            "    max_tokens: 42\n"
            "    api_base: http://localhost:11434\n"
        )
        llmmod.llm("hi")
        call = self.fake.calls[0]
        self.assertEqual(call["temperature"], 0.1)
        self.assertEqual(call["max_tokens"], 42)
        self.assertEqual(call["api_base"], "http://localhost:11434")

    def test_bad_active_raises(self):
        self._write_config(
            "active: nope\n"
            "providers:\n"
            "  gemini:\n"
            "    model: gemini/gemini-2.5-flash\n"
            "    api_key_env: GEMINI_API_KEY\n"
        )
        with self.assertRaises(ValueError):
            llmmod.active_model()


if __name__ == "__main__":
    unittest.main(verbosity=2)
