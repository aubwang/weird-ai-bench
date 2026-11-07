"""Preflight checks, with scripted completions only."""

import pytest

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


class PricedClient:
    """The small call costs $0.001; the judge-sized one $0.05. Reasoning counts are unreported."""

    def complete(self, model, messages):
        big = len(messages[0]["content"]) > 10000
        return Completion(text="ok", model=model, cost=None if model == "u/unpriced" and big else
                          (0.05 if big else 0.001), latency_s=1.0, reasoning_tokens=None)


def test_preflight_cost_includes_the_judge_size_call():
    row = cli.preflight_one(PricedClient(), "a/model", long=True)
    assert row["cost"] == pytest.approx(0.051) and row["missing_cost_calls"] == 0
    row = cli.preflight_one(PricedClient(), "u/unpriced", long=True)
    assert row["cost"] == 0.001 and row["missing_cost_calls"] == 1


def test_unreported_reasoning_is_not_treated_as_zero(monkeypatch, capsys):
    monkeypatch.setattr(cli, "OpenRouterClient", lambda **kw: PricedClient())
    assert cli.main(["preflight", "a/model", "u/unpriced", "--effort", "high", "--long"]) == 0
    out = capsys.readouterr().out
    assert "no reasoning tokens at effort" not in out
    assert "didn't report reasoning tokens" in out
    assert "$0.0510 " in out and "$0.0010+" in out
