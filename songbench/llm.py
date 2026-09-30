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
    """OpenRouter by default; SONGBENCH_BASE_URL points at any OpenAI-compatible API."""
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


class LLMError(RuntimeError):
    pass


@dataclass
class OpenRouterClient:
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int = DEFAULT_MAX_TOKENS
    effort: str | None = None  # reasoning effort, for models that support it
    seed: int | None = None
    timeout_s: float = 600.0  # long reasoning turns can run past 5 minutes
    retries: int = 4
    _http: httpx.Client | None = field(default=None, repr=False)

    def __post_init__(self):
        base = os.environ.get("SONGBENCH_BASE_URL")
        if base:
            self.api_key = self.api_key or os.environ.get("SONGBENCH_API_KEY")
        else:
            self.api_key = (self.api_key or os.environ.get("OPENROUTER_API_KEY")
                            or os.environ.get("SONGBENCH_API_KEY"))
        if not self.api_key:
            key_name = "SONGBENCH_API_KEY" if base else "OPENROUTER_API_KEY"
            raise LLMError(f"Set {key_name} to call models.")
        self.url = _endpoint(base)
        self._http = httpx.Client(timeout=self.timeout_s)

    def complete(self, model: str, messages: list[dict]) -> Completion:
        body: dict = {
            "model": model,
            "messages": messages,
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
            "X-Title": "songbench",
        }
        delay = 2.0
        last_err = ""
        for attempt in range(self.retries + 1):
            t0 = time.monotonic()
            try:
                r = self._http.post(self.url, json=body, headers=headers)
            except httpx.HTTPError as e:
                last_err = f"network error: {e}"
            else:
                if r.status_code == 200:
                    data = r.json()
                    if "error" in data:
                        last_err = str(data["error"])
                    else:
                        choice = data["choices"][0]
                        text = (choice.get("message") or {}).get("content") or ""
                        usage = data.get("usage") or {}
                        if not text.strip() and choice.get("finish_reason") == "length":
                            raise LLMError(
                                f"{model} used all {self.max_tokens} tokens before answering "
                                f"(likely reasoning); raise --max-tokens or lower --effort")
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
                            )
                elif r.status_code in (408, 429, 500, 502, 503, 504):
                    last_err = f"HTTP {r.status_code}: {r.text[:300]}"
                else:
                    raise LLMError(f"{model}: HTTP {r.status_code}: {r.text[:500]}")
            if attempt < self.retries:
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
