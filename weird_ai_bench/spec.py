"""Song templates: load and validate the YAML spec files."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import yaml


@dataclass
class InternalRhymeSpec:
    word_syllables: int | None = None
    end_word: bool = False

    def __post_init__(self):
        n = self.word_syllables
        if n is not None and (type(n) is not int or n < 1):
            raise ValueError("internal_rhyme word_syllables must be a positive whole number")
        if not isinstance(self.end_word, bool):
            raise ValueError("internal_rhyme end_word must be true or false")


@dataclass
class ProsodySetting:
    """One author-verified syllable grouping over a fixed sequence of notes.

    A span of 2 means one syllable sustained over two notes, not two syllables.
    Stress and phrase boundaries are syllable indices in this setting only.
    These annotations do not supply pitches, durations, or audio evidence.
    """

    name: str
    note_spans: list[int]
    stress: list[int] = field(default_factory=list)
    split: list[int] | None = None

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("prosody setting needs a nonempty name")
        if (not isinstance(self.note_spans, list) or not self.note_spans or
                any(type(n) is not int or n < 1 for n in self.note_spans)):
            raise ValueError("prosody note_spans must be a nonempty list of positive whole numbers")
        _validate_meter(self.syllables, self.stress, self.split)

    @property
    def syllables(self) -> int:
        return len(self.note_spans)


def _validate_meter(syllables, stress, split) -> None:
    if type(syllables) is not int or syllables < 1:
        raise ValueError("syllables must be a positive whole number")
    if (not isinstance(stress, list) or
            any(type(p) is not int or not 1 <= p <= syllables for p in stress) or
            len(set(stress)) != len(stress)):
        raise ValueError("stress must list distinct syllable positions from 1 to the syllable count")
    if split is not None and (not isinstance(split, list) or len(split) != 2 or
            any(type(n) is not int or n < 1 for n in split) or sum(split) != syllables):
        raise ValueError("split must contain two positive whole numbers summing to syllables")


@dataclass
class LineSpec:
    syllables: int | None = None
    stress: list[int] = field(default_factory=list)
    split: list[int] | None = None
    rhyme: str | None = None
    internal_rhyme: bool | InternalRhymeSpec = False
    hook: bool = False
    repeats_hook: bool = False
    refrain: str | None = None  # lines sharing an intentionally repeated phrase or ending
    echo: bool = False
    note: str | None = None
    reference: str | None = None
    adlibs: list[str] = field(default_factory=list)
    # Legacy count tolerance, not evidence that a line fits a melody.
    slack: int | list[int] = 0
    prosody: list[ProsodySetting] = field(default_factory=list)

    def __post_init__(self):
        parts = self.slack if isinstance(self.slack, list) and len(self.slack) == 2 else [self.slack]
        if any(type(x) is not int or x < 0 for x in parts):
            raise ValueError("line slack must be a whole number 0 or more, or [fewer, more]")
        if not isinstance(self.prosody, list) or any(not isinstance(p, ProsodySetting) for p in self.prosody):
            raise ValueError("prosody must be a list of settings")
        if self.prosody:
            if self.syllables is not None or self.stress or self.split is not None or any(parts):
                raise ValueError("prosody replaces line syllables, stress, split, and slack; put meter in each setting")
            if len({p.name for p in self.prosody}) != len(self.prosody):
                raise ValueError("prosody setting names must be unique within a line")
            if len({sum(p.note_spans) for p in self.prosody}) != 1:
                raise ValueError("prosody settings must cover the same total number of notes")
        else:
            _validate_meter(self.syllables, self.stress, self.split)


@dataclass
class RhymeSpec:
    slant: bool = True
    min_syllables: int = 1


@dataclass
class SectionSpec:
    key: str
    label: str
    lines: list[LineSpec]
    rhymes: dict[str, RhymeSpec]
    note: str = ""
    singer: int | None = None  # verses: which singer writes it
    sung_by: list[int] | None = None  # the shared chorus: which singers sing it
    trade: list[int] | None = None  # bridge: singer for each line

    @property
    def is_chorus(self) -> bool:
        return self.sung_by is not None

    @property
    def is_trade(self) -> bool:
        return self.trade is not None


@dataclass
class SongSpec:
    id: str
    title: str
    artist: str
    singers: int
    sections: dict[str, SectionSpec]
    generation_order: list[str]
    performance_order: list[str]
    syllable_overrides: dict[str, int]

    def chorus_key(self) -> str | None:
        for key, sec in self.sections.items():
            if sec.is_chorus:
                return key
        return None

    def reference_text(self) -> str | None:
        """Render annotated source lines as a speaker-tagged lyric reference."""
        parts = []
        for key in self.performance_order:
            sec = self.sections[key]
            if not any(line.reference for line in sec.lines):
                continue
            speaker = (group_label(sec.sung_by, self.singers) if sec.is_chorus else
                       f"Singer {sec.singer}" if sec.singer else "trading lines")
            body = []
            for i, line in enumerate(sec.lines):
                if line.reference:
                    prefix = f"Singer {sec.trade[i]}: " if sec.is_trade else ""
                    body.append(prefix + format_lyric(line.reference, line.adlibs))
            parts.append(f"[{sec.label} - {speaker}]\n" + "\n".join(body))
        return "\n\n".join(parts) if parts else None


def _line(d: dict) -> LineSpec:
    d = dict(d)
    known = LineSpec.__dataclass_fields__.keys()
    unknown = set(d) - set(known)
    if unknown:
        raise ValueError(f"unknown line fields: {sorted(unknown)}")
    prosody = d.get("prosody", [])
    if not isinstance(prosody, list):
        raise ValueError("prosody must be a list of settings")
    if "prosody" in d and not prosody and d.get("syllables") is None:
        raise ValueError("prosody must contain at least one setting")
    for p in prosody:
        if (not isinstance(p, dict) or set(p) - set(ProsodySetting.__dataclass_fields__) or
                not {"name", "note_spans"} <= set(p)):
            raise ValueError("prosody settings use name, note_spans, and optional stress and split")
    d["prosody"] = [ProsodySetting(**p) for p in prosody]
    ir = d.get("internal_rhyme", False)
    if isinstance(ir, dict):
        if set(ir) - {"word_syllables", "end_word"}:
            raise ValueError("unknown internal_rhyme fields")
        d["internal_rhyme"] = InternalRhymeSpec(**ir)
    elif not isinstance(ir, bool):
        raise ValueError("internal_rhyme must be true, false, or a mapping")
    if d.get("reference") is not None and not isinstance(d["reference"], str):
        raise ValueError("line reference must be text")
    if d.get("refrain") is not None and (not isinstance(d["refrain"], str) or
                                         not d["refrain"].strip()):
        raise ValueError("line refrain must be a nonempty group name")
    _validate_adlibs(d.get("adlibs", []))
    return LineSpec(**d)


def slack_bounds(ln: LineSpec) -> tuple[int, int]:
    """Legacy count tolerance; does not establish melody fit."""
    s = ln.slack
    return (s, s) if isinstance(s, int) else (s[0], s[1])


def load_spec(path_or_id: str | Path = "two_voices") -> SongSpec:
    """Load a spec by file path, or by id from the bundled specs."""
    p = Path(path_or_id).expanduser()
    if p.suffix in (".yaml", ".yml"):
        text = p.read_text()
    else:
        text = (
            resources.files("weird_ai_bench.data.specs")
            .joinpath(f"{path_or_id}.yaml")
            .read_text()
        )
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError("song spec must be a YAML mapping")
    if "fixed_chorus" in raw:
        raise ValueError("Move fixed_chorus into a separate sections preset and select it with --preset.")
    return spec_from_dict(raw)


def group_label(singers: list[int], total: int) -> str:
    """How prompts and sheets name a group of singers: "both", "all", "Singers 1 and 3"."""
    if len(singers) == total and total > 1:
        return "both" if total == 2 else "all"
    if len(singers) == 1:
        return f"Singer {singers[0]}"
    return "Singers " + ", ".join(map(str, singers[:-1])) + f" and {singers[-1]}"


def _sung_by(value, key: str, total: int) -> list[int] | None:
    if value is None:
        return None
    if value == "all" or (value == "both" and total == 2):
        return list(range(1, total + 1))
    if value == "both":
        raise ValueError(f"{key}: sung_by: both needs a two-singer song; use all or a list of singers")
    if not isinstance(value, list) or not value or any(not isinstance(s, int) for s in value):
        raise ValueError(f"{key}: sung_by must be all or a list of singer numbers")
    if len(set(value)) != len(value) or any(not 1 <= s <= total for s in value):
        raise ValueError(f"{key}: sung_by lists each singer once, from 1 to {total}")
    return sorted(value)


def spec_from_dict(raw: dict) -> SongSpec:
    """Rebuild and validate a YAML spec or a saved dataclass snapshot."""
    total = raw.get("singers")
    if not isinstance(total, int) or isinstance(total, bool) or total < 1:
        raise ValueError("song spec needs singers: the number of singers, 1 or more")

    sections: dict[str, SectionSpec] = {}
    for key, s in raw["sections"].items():
        rhymes = {k: RhymeSpec(**v) for k, v in (s.get("rhymes") or {}).items()}
        lines = [_line(ld) for ld in s["lines"]]
        sec = SectionSpec(
            key=key,
            label=s.get("label", key),
            lines=lines,
            rhymes=rhymes,
            note=(s.get("note") or "").strip(),
            singer=s.get("singer"),
            sung_by=_sung_by(s.get("sung_by"), key, total),
            trade=s.get("trade"),
        )
        for i, ln in enumerate(lines, 1):
            if ln.rhyme and ln.rhyme not in rhymes:
                rhymes[ln.rhyme] = RhymeSpec()
        if sec.trade and len(sec.trade) != len(lines):
            raise ValueError(f"{key}: trade list must have one singer per line")
        if not (sec.singer or sec.is_chorus or sec.is_trade):
            raise ValueError(f"{key}: needs singer, sung_by, or trade")
        if sec.singer is not None and sec.singer not in range(1, total + 1):
            raise ValueError(f"{key}: singer must be from 1 to {total}")
        if sec.trade is not None and (len(sec.trade) != len(lines) or
                                      any(s not in range(1, total + 1) for s in sec.trade)):
            raise ValueError(f"{key}: trade must specify a singer from 1 to {total} for every line")
        if sum((sec.singer is not None, sec.is_chorus, sec.is_trade)) != 1:
            raise ValueError(f"{key}: choose exactly one of singer, sung_by, or trade")
        if not lines:
            raise ValueError(f"{key}: needs at least one line")
        sections[key] = sec

    spec = SongSpec(
        id=raw["id"],
        title=raw["title"],
        artist=raw["artist"],
        singers=total,
        sections=sections,
        generation_order=raw["generation_order"],
        performance_order=raw["performance_order"],
        syllable_overrides={k.lower(): int(v) for k, v in (raw.get("syllable_overrides") or {}).items()},
    )
    for k in spec.generation_order + spec.performance_order:
        if k not in sections:
            raise ValueError(f"order references unknown section {k!r}")
    if len(spec.generation_order) != len(sections) or set(spec.generation_order) != set(sections):
        raise ValueError("generation_order must include every section exactly once")
    if set(spec.performance_order) != set(sections):
        raise ValueError("performance_order must include every section (repeats are allowed)")
    if sum(sec.is_chorus for sec in sections.values()) > 1:
        raise ValueError("only one shared chorus is supported; repeat its key in performance_order")
    sung = set()
    for sec in sections.values():
        sung.update([sec.singer] if sec.singer else sec.sung_by or sec.trade)
    missing = sorted(set(range(1, total + 1)) - sung)
    if missing:
        raise ValueError(f"singers {missing} never sing; every singer needs a section or line")
    return spec


def bundled_specs() -> list[str]:
    return sorted(p.name.removesuffix(".yaml") for p in resources.files("weird_ai_bench.data.specs").iterdir()
                  if p.name.endswith(".yaml"))


def result_spec(result: dict) -> SongSpec:
    """Prefer the immutable run snapshot; support older saved runs too."""
    if "spec_snapshot" in result:
        return spec_from_dict(result["spec_snapshot"])
    return load_spec(result.get("config", {}).get("spec") or result["spec"])


def load_preset(path_or_id: str | Path) -> dict:
    """Load prewritten sections independently of the song's pacing spec."""
    path = Path(path_or_id).expanduser()
    text = (path.read_text(encoding="utf-8") if path.suffix in (".yaml", ".yml") else
            resources.files("weird_ai_bench.data.presets").joinpath(f"{path_or_id}.yaml").read_text())
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict) or not isinstance(raw.get("song"), str):
        raise ValueError("preset needs a song ID and sections")
    sections = raw.get("sections")
    if not isinstance(sections, dict) or not sections:
        raise ValueError("preset needs a nonempty sections mapping")
    result = {}
    for key, source in sections.items():
        if not isinstance(key, str) or not isinstance(source, list) or not source:
            raise ValueError("each preset section needs a nonempty list of lines")
        lines = []
        for line in source:
            if isinstance(line, str):
                line = {"text": line}
            if not isinstance(line, dict) or set(line) - {"text", "adlibs"}:
                raise ValueError("preset lines use text and optional adlibs")
            if not isinstance(line.get("text"), str) or not line["text"].strip() or any(c in line["text"] for c in "\n\r"):
                raise ValueError("preset line text must be a nonempty single line")
            adlibs = line.get("adlibs", [])
            _validate_adlibs(adlibs)
            lines.append(format_lyric(line["text"], adlibs))
        result[key] = lines
    return {"song": raw["song"], "sections": result}


def _validate_adlibs(adlibs) -> None:
    if not isinstance(adlibs, list) or any(not isinstance(a, str) or not a.strip() or
                                         any(c in a for c in "<>\n\r") for a in adlibs):
        raise ValueError("adlibs must be a list of nonempty single-line text strings without angle brackets")


def format_lyric(text: str, adlibs: list[str]) -> str:
    return text + "".join(f" <adlib>{a}</adlib>" for a in adlibs)


def describe_internal_rhyme(rule: bool | InternalRhymeSpec) -> str:
    if isinstance(rule, bool):
        return "an internal rhyme between two of its words"
    size = f"{rule.word_syllables}-syllable " if rule.word_syllables else ""
    ending = ", with one at the end of the line" if rule.end_word else ""
    return f"a full end-sound rhyme between two different {size}words or acronyms{ending}"


def describe_line(ln: LineSpec, idx: int, rhymes: dict[str, RhymeSpec]) -> str:
    """One-line human description of a line's constraints, used in prompts."""
    fewer, more = slack_bounds(ln)
    parts = (["one complete declared prosody setting: " +
              " OR ".join(describe_setting(p) for p in ln.prosody)] if ln.prosody else
             [f"{ln.syllables} syllables" + (
                 f" (legacy count range {max(ln.syllables - fewer, 1)} to {ln.syllables + more})"
                 if fewer or more else "")])
    if ln.split and not ln.prosody:
        parts.append(f"phrased {ln.split[0]} + {ln.split[1]} with a pause (comma or dash) after syllable {ln.split[0]}")
    if ln.stress:
        parts.append("stressed syllables on " + ", ".join(str(p) for p in ln.stress))
    if ln.rhyme:
        r = rhymes.get(ln.rhyme, RhymeSpec())
        desc = f"rhyme {ln.rhyme}"
        if r.min_syllables >= 2:
            desc += " (two-syllable rhyme)"
        parts.append(desc)
    if ln.internal_rhyme:
        parts.append("contains " + describe_internal_rhyme(ln.internal_rhyme))
    if ln.hook:
        parts.append("this is the hook")
    if ln.repeats_hook:
        parts.append("ends with the hook")
    if ln.refrain:
        parts.append(f"refrain {ln.refrain}")
    if ln.echo:
        parts.append("followed by an echo of the hook's last word in parentheses")
    if ln.note:
        parts.append(ln.note)
    return f"Line {idx}: " + "; ".join(parts)


def describe_setting(setting: ProsodySetting) -> str:
    parts = [f"{setting.name}: {setting.syllables} syllables",
             "notes per syllable [" + ", ".join(map(str, setting.note_spans)) + "]"]
    if setting.stress:
        parts.append("stressed syllables on " + ", ".join(map(str, setting.stress)))
    if setting.split:
        parts.append(f"pause (comma or dash) after syllable {setting.split[0]}")
    return "(" + "; ".join(parts) + ")"


def describe_section(sec: SectionSpec) -> str:
    out = [f"{sec.label}:"]
    if sec.note:
        out.append(sec.note)
    for i, ln in enumerate(sec.lines, 1):
        out.append("  " + describe_line(ln, i, sec.rhymes))
    groups = {}
    for i, ln in enumerate(sec.lines, 1):
        if ln.rhyme:
            groups.setdefault(ln.rhyme, []).append(i)
    for g, idxs in groups.items():
        r = sec.rhymes.get(g, RhymeSpec())
        kind = "slant rhyme is fine" if r.slant else "full rhyme required"
        if len(idxs) > 1:
            out.append(f"  Rhyme {g}: lines {', '.join(map(str, idxs))} rhyme with each other ({kind}).")
    refrains: dict[str, list[int]] = {}
    for i, ln in enumerate(sec.lines, 1):
        if ln.refrain:
            refrains.setdefault(ln.refrain, []).append(i)
    for group, idxs in refrains.items():
        if len(idxs) > 1:
            out.append(f"  Refrain {group}: lines {', '.join(map(str, idxs))} reuse a short phrase "
                       "or ending; the rest of each line can change.")
    return "\n".join(out)


def slack_hints(spec: SongSpec, min_lines: int = 3) -> list[str]:
    """Flag differing legacy counts for manual review, without inferring melody.

    Kept under its old public name for compatibility. Equal section lengths do
    not establish a shared melody or justify widening the accepted counts.
    """
    secs = [s for s in spec.sections.values()
            if not s.is_chorus and not s.is_trade and len(s.lines) >= min_lines]
    hints = []
    for i, a in enumerate(secs):
        for b in secs[i + 1:]:
            if len(a.lines) != len(b.lines):
                continue
            diffs = {n: abs(x.syllables - y.syllables)
                     for n, (x, y) in enumerate(zip(a.lines, b.lines), 1)
                     if not x.prosody and not y.prosody and x.syllables != y.syllables
                     and not any(slack_bounds(x) + slack_bounds(y))}
            if diffs:
                hints.append(
                    f"{a.label} and {b.label} differ by up to {max(diffs.values())} "
                    f"syllable{'s' if max(diffs.values()) > 1 else ''} on "
                    f"line{'s' if len(diffs) > 1 else ''} {', '.join(map(str, diffs))}. "
                    "Check the source phrasing; equal section lengths do not establish a shared melody. "
                    "Use explicit `prosody` settings only for verified alternatives.")
    return hints


def syllable_map(spec: SongSpec) -> str:
    """Compact overview of the whole song, for judges."""
    rows = []
    for key in spec.performance_order:
        sec = spec.sections[key]
        counts = " / ".join(
            " OR ".join(describe_setting(p) for p in ln.prosody) if ln.prosody else
            f"{ln.split[0]}+{ln.split[1]}" if ln.split else str(ln.syllables) for ln in sec.lines
        )
        rows.append(f"{sec.label}: {counts}")
    seen = []
    for r in rows:
        if r not in seen:
            seen.append(r)
    return "\n".join(seen)
