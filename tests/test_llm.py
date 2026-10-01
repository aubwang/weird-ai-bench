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
