"""Model clients. OpenRouter for real runs; a scripted fake for tests and dry runs."""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MAX_TOKENS = 32000  # reasoning models can spend 8k+ thinking before they write a line


def _endpoint(base: str | None) -> str:
    """OpenRouter by default; WEIRD_AI_BENCH_BASE_URL points at any OpenAI-compatible API."""
    return base.rstrip("/") + "/chat/completions" if base else OPENROUTER_URL


@dataclass
class Completion:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float | None = None
    latency_s: float = 0.0
    raw_finish: str | None = None
    reasoning_tokens: int | None = None  # when the provider reports them
    cached_tokens: int | None = None


class LLMError(RuntimeError):
    pass


_RETRYABLE = (408, 429, 500, 502, 503, 504)
_EPHEMERAL = {"type": "ephemeral"}


def cache_marked(model: str, messages: list[dict]) -> list[dict]:
    """Messages as sent: prompt-cache breakpoints for Anthropic models, plain text otherwise.

    Caching changes billing, not what the model reads: the text is identical either way.
    OpenAI, Google and most other providers cache repeated prefixes automatically. Anthropic
    caches only up to explicit breakpoints, so mark the system prompt, the end of the
    conversation so far (the next turn reuses it), and any shared prefix a caller declares
    with an optional "cache_prefix" (a character count) on a message, such as the judge's
    setup that every pair in a group shares. Anthropic allows four breakpoints; this uses
    at most three.
    """
    anthropic = family(model) == "anthropic"
    out = []
    last = len(messages) - 1
    for i, m in enumerate(messages):
        m = {k: v for k, v in m.items() if k != "cache_prefix"}
        text = m.get("content")
        if not anthropic or not isinstance(text, str) or not text:
            out.append(m)
            continue
        cut = messages[i].get("cache_prefix")
        parts = ([{"type": "text", "text": text[:cut], "cache_control": _EPHEMERAL},
                  {"type": "text", "text": text[cut:]}]
                 if isinstance(cut, int) and 0 < cut < len(text) else [{"type": "text", "text": text}])
        if (i == 0 and m.get("role") == "system") or i == last:
            parts[-1] = {**parts[-1], "cache_control": _EPHEMERAL}
        out.append({**m, "content": parts})
    return out


def _retry_after(value: str | None) -> float | None:
    """Seconds from a Retry-After header given in seconds; dates are ignored."""
    try:
        return max(float(value), 0.0) if value is not None else None
    except ValueError:
        return None


@dataclass
class OpenRouterClient:
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int = DEFAULT_MAX_TOKENS
    effort: str | None = None  # reasoning effort, for models that support it
    seed: int | None = None
    timeout_s: float = 600.0  # long reasoning turns can run past 5 minutes
    retries: int = 4
    # Upstream rate limits on shared capacity can last minutes, longer than the
    # short backoff for transient errors. Waits double from 5s, capped at a minute.
    rate_limit_retries: int = 8
    rate_limit_max_wait_s: float = 60.0
    _http: httpx.Client | None = field(default=None, repr=False)

    def __post_init__(self):
        base = os.environ.get("WEIRD_AI_BENCH_BASE_URL")
        if base:
            self.api_key = self.api_key or os.environ.get("WEIRD_AI_BENCH_API_KEY")
        else:
            self.api_key = (self.api_key or os.environ.get("OPENROUTER_API_KEY")
                            or os.environ.get("WEIRD_AI_BENCH_API_KEY"))
        if not self.api_key:
            key_name = "WEIRD_AI_BENCH_API_KEY" if base else "OPENROUTER_API_KEY"
            raise LLMError(f"Set {key_name} to call models.")
        self.url = _endpoint(base)
        self._http = httpx.Client(timeout=self.timeout_s)

    def complete(self, model: str, messages: list[dict]) -> Completion:
        body: dict = {
            "model": model,
            "messages": cache_marked(model, messages),
            "max_tokens": self.max_tokens,
            "usage": {"include": True},
        }
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if self.seed is not None:
            body["seed"] = self.seed
        if self.effort:
            body["reasoning"] = {"effort": self.effort}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Title": "weird-ai-bench",
        }
        delay, limit_delay = 2.0, 5.0
        last_err = ""
        attempt = limited = 0
        while True:
            t0 = time.monotonic()
            wait = None  # seconds a rate limit asked for, when it said
            rate_limited = False
            try:
                r = self._http.post(self.url, json=body, headers=headers)
            except httpx.HTTPError as e:
                last_err = f"network error: {e}"
            else:
                if r.status_code == 200:
                    data = r.json()
                    if "error" in data:
                        err = data["error"]
                        code = err.get("code") if isinstance(err, dict) else None
                        last_err = str(err)
                        if code == 429:
                            rate_limited = True
                        elif isinstance(code, int) and code not in _RETRYABLE:
                            raise LLMError(f"{model}: {last_err}")
                    else:
                        choice = data["choices"][0]
                        text = (choice.get("message") or {}).get("content") or ""
                        usage = data.get("usage") or {}
                        if not text.strip() and choice.get("finish_reason") == "length":
                            raise LLMError(
                                f"{model} used all {self.max_tokens} tokens before answering "
                                f"(likely reasoning); raise --max-tokens or lower --effort")
                        if not text.strip() and choice.get("finish_reason") == "content_filter":
                            # A refusal repeats for the same request; retrying only spends money.
                            raise LLMError(f"{model}: empty response (finish_reason=content_filter)")
                        if not text.strip():
                            last_err = f"empty response (finish_reason={choice.get('finish_reason')})"
                        else:
                            return Completion(
                                text=text,
                                model=data.get("model", model),
                                prompt_tokens=usage.get("prompt_tokens", 0),
                                completion_tokens=usage.get("completion_tokens", 0),
                                cost=usage.get("cost"),
                                latency_s=time.monotonic() - t0,
                                raw_finish=choice.get("finish_reason"),
                                reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                                cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                            )
                elif r.status_code in _RETRYABLE:
                    last_err = f"HTTP {r.status_code}: {r.text[:300]}"
                    if r.status_code == 429:
                        rate_limited = True
                        wait = _retry_after(r.headers.get("retry-after"))
                else:
                    raise LLMError(f"{model}: HTTP {r.status_code}: {r.text[:500]}")
            if rate_limited:
                if limited >= self.rate_limit_retries:
                    break
                limited += 1
                pause = wait if wait is not None else limit_delay
                time.sleep(min(pause, self.rate_limit_max_wait_s) + random.random())
                limit_delay = min(limit_delay * 2, self.rate_limit_max_wait_s)
                continue
            if attempt >= self.retries:
                break
            attempt += 1
            time.sleep(delay + random.random())
            delay *= 2
        raise LLMError(f"{model}: {last_err}")


@dataclass
class ScriptedClient:
    """Returns canned responses in order. For tests and --dry-run."""

    responses: list[str] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)

    def complete(self, model: str, messages: list[dict]) -> Completion:
        self.calls.append({"model": model, "messages": [dict(m) for m in messages]})
        text = self.responses.pop(0) if self.responses else "<lyrics>\n</lyrics>"
        return Completion(text=text, model=model, prompt_tokens=0, completion_tokens=0, cost=0.0)


# Model-name prefixes for ids without a vendor ("claude-sonnet-5" on an OpenAI-compatible proxy).
_NAME_FAMILY = {
    "claude": "anthropic",
    "gpt": "openai", "chatgpt": "openai", "o1": "openai", "o3": "openai", "o4": "openai",
    "openai": "openai",
    "gemini": "google", "gemma": "google",
    "llama": "meta-llama",
    "grok": "x-ai",
    "deepseek": "deepseek",
    "qwen": "qwen",
    "mistral": "mistralai", "mixtral": "mistralai", "codestral": "mistralai",
}
_VENDOR_FAMILY = {"meta": "meta-llama", "xai": "x-ai", "mistral": "mistralai", "claude": "anthropic"}


def _known_family(mid: str) -> str | None:
    """Family of a lowercase id by its vendor prefix or model name; None when unrecognised."""
    if "/" in mid:
        vendor, rest = mid.split("/", 1)
        vendor = _VENDOR_FAMILY.get(vendor, vendor)
        return vendor if vendor in _NAME_FAMILY.values() else _known_family(rest)
    name = mid.split(":")[0]
    for key in sorted(_NAME_FAMILY, key=len, reverse=True):
        if name.startswith(key) and not name[len(key):len(key) + 1].isalpha():
            return _NAME_FAMILY[key]
    return None


def family(model_id: str) -> str:
    """Provider family: 'openai/gpt-5' -> 'openai', and a bare 'gpt-5' -> 'openai' too.

    Known vendors and model names are normalised. Otherwise a prefixed id is its vendor
    ('provider/model-a' -> 'provider') and a bare id is its own family.
    """
    mid = model_id.strip().lower()
    return _known_family(mid) or (mid.split("/", 1)[0] if "/" in mid else mid)


def display_name(model_id: str) -> str:
    """A readable default name: 'anthropic/claude-sonnet-5' -> 'claude-sonnet-5'."""
    return model_id.split("/", 1)[-1].split(":")[0]
