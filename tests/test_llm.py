"""Credential routing tests; requests are handled entirely in memory."""

import httpx
import pytest

from weird_ai_bench.llm import LLMError, OpenRouterClient, OPENROUTER_URL, family


@pytest.mark.parametrize("base,router,song,explicit,expected", [
    (None, "router-test", "song-test", None, "router-test"),
    ("", "router-test", "song-test", None, "router-test"),
    (None, None, "song-test", None, "song-test"),
    (None, "router-test", "song-test", "explicit-test", "explicit-test"),
    ("https://custom.invalid/v1/", "router-test", "song-test", None, "song-test"),
    ("http://localhost:11434/v1", "router-test", None, "explicit-test", "explicit-test"),
])
def test_credentials_sent_to_selected_endpoint(monkeypatch, base, router, song, explicit, expected):
    for key, value in (("WEIRD_AI_BENCH_BASE_URL", base), ("OPENROUTER_API_KEY", router),
                       ("WEIRD_AI_BENCH_API_KEY", song)):
        monkeypatch.delenv(key, raising=False)
        if value is not None:
            monkeypatch.setenv(key, value)
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        monkeypatch.setattr("weird_ai_bench.llm.httpx.Client", lambda **kwargs: http)
        client = OpenRouterClient(api_key=explicit)
        assert client.complete("test/model", []).text == "hello"
    assert len(requests) == 1
    assert requests[0].headers["Authorization"] == f"Bearer {expected}"
    assert str(requests[0].url) == (base.rstrip("/") + "/chat/completions" if base else OPENROUTER_URL)


@pytest.mark.parametrize("base", ["https://custom.invalid/v1/", "http://localhost:11434/v1"])
def test_custom_endpoint_never_falls_back_to_router_key(monkeypatch, base):
    monkeypatch.setenv("WEIRD_AI_BENCH_BASE_URL", base)
    monkeypatch.setenv("OPENROUTER_API_KEY", "router-test")
    monkeypatch.delenv("WEIRD_AI_BENCH_API_KEY", raising=False)

    def unexpected_client(**kwargs):
        pytest.fail("Missing custom credential should fail before HTTP client creation")

    monkeypatch.setattr("weird_ai_bench.llm.httpx.Client", unexpected_client)
    with pytest.raises(LLMError, match="WEIRD_AI_BENCH_API_KEY"):
        OpenRouterClient()


@pytest.mark.parametrize("model,expected", [
    ("openai/gpt-5", "openai"),
    ("anthropic/claude-sonnet-5:thinking", "anthropic"),
    ("meta-llama/llama-4", "meta-llama"),
    ("x-ai/grok-4", "x-ai"),
    ("google/gemini-3", "google"),
    ("Meta/Llama-4", "meta-llama"),
    ("xai/grok-4", "x-ai"),
    ("provider/model-a", "provider"),
    ("claude-sonnet-5", "anthropic"),
    ("gpt-5", "openai"),
    ("chatgpt-4o-latest", "openai"),
    ("o3-mini", "openai"),
    ("o4", "openai"),
    ("gemini-3-pro", "google"),
    ("gemma3", "google"),
    ("llama3.1-70b", "meta-llama"),
    ("grok-4", "x-ai"),
    ("deepseek-r1", "deepseek"),
    ("qwen2.5-72b", "qwen"),
    ("mixtral-8x7b", "mistralai"),
    ("codestral", "mistralai"),
    ("azure/gpt-5", "openai"),
    ("model-a", "model-a"),
    ("ollama-mini", "ollama-mini"),
    ("omega", "omega"),
])
def test_family(model, expected):
    assert family(model) == expected


def _scripted_http(monkeypatch, replies):
    """An OpenRouterClient whose HTTP replies come from `replies`; sleeps are recorded, not taken."""
    requests, sleeps = [], []

    def respond(request):
        requests.append(request)
        status, payload, headers = replies.pop(0)
        return httpx.Response(status, json=payload, headers=headers or {})

    http = httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr("weird_ai_bench.llm.httpx.Client", lambda **kwargs: http)
    monkeypatch.setattr("weird_ai_bench.llm.time.sleep", sleeps.append)
    monkeypatch.setattr("weird_ai_bench.llm.random.random", lambda: 0.0)
    return OpenRouterClient(api_key="test"), requests, sleeps


LIMITED = {"error": {"message": "temporarily rate-limited upstream", "code": 429}}
OK = {"choices": [{"message": {"content": "hello"}}]}


def test_upstream_rate_limit_waits_longer_than_transient_errors(monkeypatch):
    client, requests, sleeps = _scripted_http(monkeypatch, [(200, LIMITED, None)] * 6 + [(200, OK, None)])
    assert client.complete("test/model", []).text == "hello"
    assert len(requests) == 7
    assert sleeps == [5, 10, 20, 40, 60, 60]  # past the ~30s the transient backoff allows


def test_rate_limit_honors_retry_after_and_gives_up_eventually(monkeypatch):
    client, _, sleeps = _scripted_http(monkeypatch, [(429, {}, {"retry-after": "7"})] + [(200, LIMITED, None)] * 9)
    with pytest.raises(LLMError, match="rate-limited"):
        client.complete("test/model", [])
    assert sleeps[0] == 7 and len(sleeps) == client.rate_limit_retries


@pytest.mark.parametrize("payload", [
    {"error": {"message": "invalid model", "code": 400}},
    {"choices": [{"message": {"content": ""}, "finish_reason": "content_filter"}]},
])
def test_errors_that_repeat_are_not_retried(monkeypatch, payload):
    client, requests, sleeps = _scripted_http(monkeypatch, [(200, payload, None)])
    with pytest.raises(LLMError):
        client.complete("test/model", [])
    assert len(requests) == 1 and sleeps == []
