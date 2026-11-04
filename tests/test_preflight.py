"""Preflight checks, with scripted completions only."""

from weird_ai_bench import cli
from weird_ai_bench.llm import Completion, LLMError


class FakeClient:
    def __init__(self, behavior):
        self.behavior = behavior

    def complete(self, model, messages):
        kind = self.behavior[model]
        if kind == "down":
            raise LLMError(f"{model}: rate-limited upstream")
        if kind == "long-limited" and len(messages[0]["content"]) > 10000:
            raise LLMError(f"{model}: rate-limited upstream")
        return Completion(text="ok", model=model, cost=0.001, latency_s=1.0,
                          reasoning_tokens=0 if kind == "silent" else 40)


def test_preflight_flags_failures_silent_reasoning_and_size_limits(monkeypatch, capsys):
    behavior = {"a/ready": "ok", "b/silent": "silent", "c/down": "down", "d/big": "long-limited"}
    monkeypatch.setattr(cli, "OpenRouterClient", lambda **kw: FakeClient(behavior))
    code = cli.main(["preflight", *behavior, "--effort", "high", "--long"])
    out = capsys.readouterr().out
    assert code == 1
    assert "no reasoning tokens at effort high" in out and "b/silent" in out
    assert out.count("FAIL") == 2  # c/down's call and d/big's judge-size prompt


def test_preflight_passes_when_every_model_is_ready(monkeypatch):
    monkeypatch.setattr(cli, "OpenRouterClient", lambda **kw: FakeClient({"a/ready": "ok"}))
    assert cli.main(["preflight", "a/ready", "--effort", "high"]) == 0
