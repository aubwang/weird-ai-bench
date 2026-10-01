"""Scenario files: the framing the singers get, such as what they're writing and who they address.

The runner adds only mechanics on top of a scenario: the cast of singers, the
output-format rules, and the song's reference lyrics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import yaml

_PLACEHOLDER = re.compile(r"\{(title|artist|singers)\}")


@dataclass
class Scenario:
    id: str
    text: str
    per_singer: dict[int, str] = field(default_factory=dict)
    min_singers: int = 1
    max_singers: int | None = None
    requires_names: bool = False

    def render(self, spec, singer: int | None = None) -> str:
        """The common framing, plus this singer's own text when a singer is given."""
        parts = [_fill(self.text, spec)]
        if singer is not None:
            parts.append(self.singer_text(spec, singer))
        return "\n\n".join(p for p in parts if p)

    def singer_text(self, spec, singer: int) -> str:
        return _fill(self.per_singer.get(singer, ""), spec)


def _fill(text: str, spec) -> str:
    values = {"title": spec.title, "artist": spec.artist, "singers": str(spec.singers)}
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], text).strip()


def scenario_from_dict(raw: dict) -> Scenario:
    """Rebuild and validate a scenario from YAML or a saved snapshot."""
    if not isinstance(raw, dict):
        raise ValueError("scenario must be a YAML mapping")
    unknown = set(raw) - set(Scenario.__dataclass_fields__)
    if unknown:
        raise ValueError(f"unknown scenario fields: {sorted(unknown)}")
    if not isinstance(raw.get("id"), str) or not raw["id"].strip():
        raise ValueError("scenario needs an id")
    if not isinstance(raw.get("text", ""), str):
        raise ValueError("scenario text must be text")
    per = raw.get("per_singer") or {}
    if not isinstance(per, dict) or any(not isinstance(v, str) for v in per.values()):
        raise ValueError("per_singer maps singer numbers to text")
    try:
        per = {int(k): v for k, v in per.items()}
    except (TypeError, ValueError):
        raise ValueError("per_singer keys must be singer numbers") from None
    sc = Scenario(
        id=raw["id"],
        text=raw.get("text") or "",
        per_singer=per,
        min_singers=int(raw.get("min_singers", 1)),
        max_singers=None if raw.get("max_singers") is None else int(raw["max_singers"]),
        requires_names=bool(raw.get("requires_names", False)),
    )
    if sc.min_singers < 1 or (sc.max_singers is not None and sc.max_singers < sc.min_singers):
        raise ValueError("scenario singer limits need 1 <= min_singers <= max_singers")
    if any(k < 1 or (sc.max_singers is not None and k > sc.max_singers) for k in per):
        raise ValueError("per_singer names a singer outside the scenario's singer limits")
    return sc


def load_scenario(path_or_id: str | Path = "each_other") -> Scenario:
    """Load a scenario by file path, or by id from the bundled scenarios."""
    p = Path(path_or_id).expanduser()
    if p.suffix in (".yaml", ".yml"):
        text = p.read_text(encoding="utf-8")
    else:
        try:
            text = resources.files("weird_ai_bench.data.scenarios").joinpath(f"{path_or_id}.yaml").read_text()
        except FileNotFoundError:
            raise ValueError(f"no bundled scenario {str(path_or_id)!r}; "
                             f"choose from {', '.join(bundled_scenarios())} or pass a YAML path") from None
    return scenario_from_dict(yaml.safe_load(text))


def bundled_scenarios() -> list[str]:
    return sorted(p.name.removesuffix(".yaml") for p in resources.files("weird_ai_bench.data.scenarios").iterdir()
                  if p.name.endswith(".yaml"))
