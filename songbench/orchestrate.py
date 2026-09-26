"""Run one song: relay turns between the singers' models, check each part, save a transcript."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .llm import display_name
from .prompts import (
    trade_line_task, chorus_task, label, parse_lyrics, render_song_so_far,
    retry_message, section_task, system_prompt,
)
from .scenario import Scenario, load_scenario, scenario_from_dict
from .spec import SongSpec, format_lyric, group_label, load_preset, load_spec, result_spec
from .verify import GATES, LineReport, SectionReport, originality, rhyme_credit, verify_section

NAMES = ("real", "assigned", "anonymous")
CHORUS = ("auto", "fixed", "original")  # or a singer number, who writes it
TRACKS = ("strict", "freeform")
GUIDANCE = ("full", "none")  # none: no song map in the prompts, only the reference lyrics


class ConfigError(ValueError):
    pass


@dataclass
class RunConfig:
    models: list[str]  # one per singer, in singer order
    scenario: str = "each_other"  # bundled scenario id or YAML path
    names: str = "real"
    personas: list[str | None] = field(default_factory=list)
    chorus: str = "auto"
    presets: list[str] = field(default_factory=list)
    track: str = "strict"
    guidance: str = "full"
    max_retries: int = 3
    tolerance: int = 0
    gates: list[str] = field(default_factory=lambda: list(GATES))
    spec: str = "two_voices"
    temperature: float | None = None
    effort: str | None = None
    seed: int | None = None

    def validate(self, spec: SongSpec | None = None, scenario: Scenario | None = None) -> None:
        """Check the settings; with a spec and scenario, also check they fit this song."""
        self.chorus = str(self.chorus)
        for name, val, allowed in (("names", self.names, NAMES), ("track", self.track, TRACKS),
                                   ("guidance", self.guidance, GUIDANCE)):
            if val not in allowed:
                raise ConfigError(f"{name} must be one of {', '.join(allowed)}; got {val!r}")
        if self.guidance == "none" and self.track != "freeform":
            # Retry feedback names the failed checks, which would hand back the song map.
            raise ConfigError("guidance=none is one-shot; use --track freeform.")
        if self.chorus not in CHORUS and not self.chorus.isdigit():
            raise ConfigError(f"chorus must be one of {', '.join(CHORUS)} or a singer number; "
                              f"got {self.chorus!r}")
        if not self.models:
            raise ConfigError("give one model per singer.")
        n = len(self.models)
        if self.personas and len(self.personas) != n:
            raise ConfigError(f"give one persona per singer: {n} models, {len(self.personas)} personas.")
        if self.names == "assigned" and not (self.personas and all(self.personas)):
            raise ConfigError("names=assigned needs a --persona for every singer.")
        bad = [g for g in self.gates if g not in GATES]
        if bad:
            raise ConfigError(f"unknown gates {bad}; choose from {', '.join(GATES)}")
        if self.names == "real":
            given = self.personas or [None] * n
            self.personas = [p or display_name(m) for p, m in zip(given, self.models)]
        elif self.names == "anonymous":
            self.personas = [None] * n
        if spec is not None and n != spec.singers:
            raise ConfigError(f"{spec.id} has {spec.singers} singer{'s' if spec.singers != 1 else ''}; "
                              f"got {n} model{'s' if n != 1 else ''}.")
        if scenario is not None:
            if n < scenario.min_singers or (scenario.max_singers is not None and n > scenario.max_singers):
                most = f" to {scenario.max_singers}" if scenario.max_singers != scenario.min_singers else ""
                raise ConfigError(f"scenario {scenario.id} is for {scenario.min_singers}"
                                  f"{most if scenario.max_singers else ' or more'} singers; got {n}.")
            if scenario.requires_names and self.names == "anonymous":
                raise ConfigError(
                    f"names=anonymous can't be combined with scenario {scenario.id}: it needs "
                    f"named singers, or the first singer would have nothing specific to respond to.")
        if spec is not None and self.chorus.isdigit():
            ck = spec.chorus_key()
            if ck is None:
                raise ConfigError(f"{spec.id} has no shared chorus to write.")
            if int(self.chorus) not in spec.sections[ck].sung_by:
                raise ConfigError(f"singer {self.chorus} doesn't sing the {spec.sections[ck].label.lower()}.")


def line_score(l: LineReport) -> float:
    checks = [1.0 if l.syllables_ok else 0.0]
    if l.stress_required:
        checks.append(l.stress_hits / l.stress_required)
    rhyme = rhyme_credit(l)
    if rhyme is not None:
        checks.append(rhyme)
    for v in (l.split_ok, l.internal_ok, l.hook_ok):
        if v is not None:
            checks.append(1.0 if v else 0.0)
    return sum(checks) / len(checks)


class Song:
    def __init__(self, cfg: RunConfig, client, spec: SongSpec | None = None,
                 scenario: Scenario | None = None, log=None):
        self.spec = spec or load_spec(cfg.spec)
        try:
            self.scenario = scenario or load_scenario(cfg.scenario)
        except (OSError, ValueError) as e:
            raise ConfigError(f"Cannot load scenario: {e}") from e
        cfg.validate(self.spec, self.scenario)
        self.cfg = cfg
        self.client = client
        self.ov = self.spec.syllable_overrides
        self.log = log or (lambda msg: None)
        self.reference_text = self.spec.reference_text()
        if cfg.guidance == "none" and self.reference_text is None:
            raise ConfigError(f"guidance=none needs reference lyrics in {self.spec.id}; "
                              f"without them the singers have nothing to go on.")
        self.singers = range(1, self.spec.singers + 1)
        self.threads = {
            s: [{"role": "system", "content": system_prompt(
                self.spec, cfg, self.scenario, s, self.reference_text)}]
            for s in self.singers
        }
        self.written: dict[str, list[str]] = {}
        self.authors: dict[str, object] = {}
        ck = self.spec.chorus_key()
        for name in cfg.presets:
            try:
                preset = load_preset(name)
            except (OSError, ValueError) as e:
                raise ConfigError(f"Cannot load --preset: {e}") from e
            if preset["song"] != self.spec.id:
                raise ConfigError(f"Preset is for {preset['song']}, not {self.spec.id}.")
            for key, lines in preset["sections"].items():
                if key not in self.spec.sections:
                    raise ConfigError(f"Preset references unknown section {key!r}.")
                if key in self.written:
                    raise ConfigError(f"Multiple presets supply section {key!r}.")
                if len(lines) != len(self.spec.sections[key].lines):
                    raise ConfigError(f"{key} needs exactly {len(self.spec.sections[key].lines)} lines; got {len(lines)}.")
                self.written[key] = list(lines)
                self.authors[key] = "fixed"
        if ck in self.written and cfg.chorus not in ("auto", "fixed"):
            raise ConfigError("Preset supplies the chorus; use --chorus auto/fixed or remove that preset section.")
        if ck and cfg.chorus == "auto":
            cfg.chorus = "fixed" if ck in self.written else str(self.spec.sections[ck].sung_by[0])
        if ck and cfg.chorus == "fixed" and ck not in self.written:
            raise ConfigError("chorus=fixed needs a --preset supplying the chorus.")
        if ck and cfg.chorus == "original":
            source = self.spec.sections[ck].lines
            if not all(ls.reference for ls in source):
                raise ConfigError("chorus=original needs a reference on every chorus line in the song YAML.")
            self.written[ck] = [format_lyric(ls.reference, ls.adlibs) for ls in source]
            self.authors[ck] = "original"
        self.turns: list[dict] = []
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0, "calls": 0}

    def model(self, singer: int) -> str:
        return self.cfg.models[singer - 1]

    # ------------------------------------------------------------ turns

    def _turn(self, singer: int, section: str, task: str, check, n_lines: int,
              single: bool = False, line_index: int | None = None) -> list[str]:
        cfg = self.cfg
        thread = self.threads[singer]
        thread.append({"role": "user", "content": task})
        max_attempts = 1 + cfg.max_retries if cfg.track == "strict" else 1
        attempts = []
        lines: list[str] = []
        for a in range(max_attempts):
            comp = self.client.complete(self.model(singer), thread)
            self.usage["calls"] += 1
            self.usage["prompt_tokens"] += comp.prompt_tokens
            self.usage["completion_tokens"] += comp.completion_tokens
            if comp.cost:
                self.usage["cost"] += comp.cost
            thread.append({"role": "assistant", "content": comp.text})
            lines = parse_lyrics(comp.text)
            if single:
                lines = lines[:1] if lines else []
            rep: SectionReport = check(lines, len(parse_lyrics(comp.text)))
            passed = rep.passed(cfg.gates)
            errors = rep.errors(cfg.gates)
            attempts.append({
                "attempt": a + 1, "response": comp.text, "lines": lines,
                "passed": passed, "errors": errors, "all_errors": rep.errors(GATES),
                "model_reported": comp.model, "latency_s": round(comp.latency_s, 2),
                "tokens": [comp.prompt_tokens, comp.completion_tokens], "cost": comp.cost,
            })
            self.log(f"  {section}{'' if line_index is None else f' line {line_index + 1}'} "
                     f"({label(cfg, singer)}) attempt {a + 1}: "
                     f"{'pass' if passed else f'{len(errors)} issue(s)'}")
            if cfg.track == "freeform" or passed or a == max_attempts - 1:
                break
            thread.append({"role": "user", "content": retry_message(
                errors, self.spec.sections[section], n_lines, single)})
        self.turns.append({
            "singer": singer, "model": self.model(singer), "section": section,
            "line_index": line_index, "attempts": attempts,
            "first_try_pass": attempts[0]["passed"], "final_pass": attempts[-1]["passed"],
            "retries": len(attempts) - 1,
        })
        return lines

    def _hook(self) -> str | None:
        for key in self.spec.generation_order:
            for ls, text in zip(self.spec.sections[key].lines, self.written.get(key, [])):
                if ls.hook:
                    return text
        return None

    def _write_section(self, key: str, singer: int, task: str) -> None:
        sec = self.spec.sections[key]
        hook = self._hook()

        def check(lines, _n):
            return verify_section(lines, sec, self.ov, self.cfg.tolerance, hook=hook)

        self.written[key] = self._turn(singer, key, task, check, len(sec.lines))
        self.authors[key] = singer

    def _write_trade(self, key: str) -> None:
        sec = self.spec.sections[key]
        self.written[key] = []
        self.authors[key] = list(sec.trade)
        for idx, singer in enumerate(sec.trade):
            so_far = render_song_so_far(self.spec, self.cfg, self.written, self.authors)
            task = trade_line_task(self.spec, self.cfg, sec, idx, so_far)
            prev = list(self.written[key])

            def check(lines, n_raw, idx=idx, prev=prev):
                full = verify_section(prev + lines, sec, self.ov, self.cfg.tolerance,
                                      upto=idx + 1, hook=self._hook())
                rep = SectionReport(section=key, lines=full.lines[idx:idx + 1], expected_lines=1)
                rep.structure_errors = [e for e in full.structure_errors if e.startswith(f"Line {idx + 1} ")]
                if not lines:
                    rep.structure_errors.append("Write exactly one lyric line between the tags.")
                elif n_raw > 1:
                    rep.structure_errors.append("Write exactly one line; you wrote several.")
                rep.rhyme_errors = [e for e in full.rhyme_errors if e.startswith(f"Line {idx + 1} ")]
                return rep

            lines = self._turn(singer, key, task, check, 1, single=True, line_index=idx)
            self.written[key].append(lines[0] if lines else "")

    # -------------------------------------------------------------- run

    def run(self) -> dict:
        cfg, spec = self.cfg, self.spec
        started = time.time()
        for key in spec.generation_order:
            if key in self.written:
                continue
            sec = spec.sections[key]
            if sec.is_chorus:
                singer = int(cfg.chorus)
                self.log(f"{sec.label}: {label(cfg, singer)} writes it")
                so_far = render_song_so_far(spec, cfg, self.written, self.authors)
                self._write_section(key, singer, chorus_task(spec, cfg, sec, so_far))
            elif sec.is_trade:
                self.log(f"{sec.label}: trading lines")
                self._write_trade(key)
            else:
                self.log(f"{sec.label}: {label(cfg, sec.singer)}")
                so_far = render_song_so_far(spec, cfg, self.written, self.authors)
                self._write_section(key, sec.singer, section_task(spec, cfg, sec, so_far))

        return self._result(time.time() - started)

    # ----------------------------------------------------------- result

    def _result(self, elapsed: float) -> dict:
        cfg, spec = self.cfg, self.spec
        hook = self._hook()
        verification = {}
        line_scores: dict[int, list[float]] = {s: [] for s in self.singers}
        for key in spec.generation_order:
            sec = spec.sections[key]
            lines = self.written.get(key, [])
            rep = verify_section(lines, sec, self.ov, cfg.tolerance, hook=hook)
            verification[key] = rep.to_dict()
            author = self.authors.get(key)
            per_line = [line_score(l) for l in rep.lines] + [0.0] * (len(sec.lines) - len(rep.lines))
            if isinstance(author, list):
                for s, sc in zip(author, per_line):
                    line_scores[s].append(sc)
            elif author in line_scores:
                line_scores[author].extend(per_line)

        by_singer = {}
        for s in self.singers:
            turns = [t for t in self.turns if t["singer"] == s]
            by_singer[str(s)] = {
                "model": self.model(s),
                "adherence": (sum(line_scores[s]) / len(line_scores[s])) if line_scores[s] else None,
                "turns": len(turns),
                "first_try_pass_rate": (sum(t["first_try_pass"] for t in turns) / len(turns)) if turns else None,
                "final_pass_rate": (sum(t["final_pass"] for t in turns) / len(turns)) if turns else None,
                "retries": sum(t["retries"] for t in turns),
            }
        generated = [k for k in spec.generation_order if self.authors.get(k) not in ("fixed", "original")]
        result = {
            "version": 2,
            "id": _run_id(cfg, self.scenario.id),
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "spec": spec.id,
            "spec_snapshot": asdict(spec),
            "scenario_snapshot": asdict(self.scenario),
            "config": asdict(cfg),
            "reference_lyrics": ({"sha256": hashlib.sha256(self.reference_text.encode("utf-8")).hexdigest()}
                                 if self.reference_text is not None else None),
            "parts": {k: {"lines": self.written.get(k, []), "author": self.authors.get(k)}
                      for k in spec.generation_order},
            "verification": verification,
            "scores": {
                "by_singer": by_singer,
                "adherence": {k: verification[k]["scores"]["overall"] for k in generated},
                "strict_pass": all(t["final_pass"] for t in self.turns),
            },
            "turns": self.turns,
            "usage": {**self.usage, "elapsed_s": round(elapsed, 1)},
            "threads": {str(k): v for k, v in self.threads.items()},
        }
        original_text = self.reference_text
        if original_text is not None:
            gen_lines = [l for k in generated for l in self.written.get(k, [])]
            result["originality"] = originality(gen_lines, original_text)
        return result


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def _run_id(cfg: RunConfig, scenario_id: str) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    cast = "-x-".join(_slug(display_name(m))[:24] for m in cfg.models)
    blind = "-unguided" if cfg.guidance == "none" else ""
    return (f"{ts}-{cast}-{_slug(scenario_id)}-{cfg.names}-{cfg.chorus}-{cfg.track}{blind}-"
            f"{uuid.uuid4().hex[:4]}")


def result_scenario(result: dict) -> Scenario:
    return scenario_from_dict(result["scenario_snapshot"])


# ------------------------------------------------------------- rendering

def render_sheet(result: dict, spec: SongSpec | None = None, blind: bool = False,
                 show_scores: bool = True) -> str:
    spec = spec or result_spec(result)
    cfg = result["config"]
    singers = range(1, len(cfg["models"]) + 1)
    names = dict(zip(singers, cfg["personas"]))
    models = dict(zip(singers, cfg["models"]))

    def who(s: int) -> str:
        if blind:
            return f"Singer {s}"
        n = names[s]
        return f"Singer {s}: {n} ({models[s]})" if n and n != models[s] else f"Singer {s}: {models[s]}"

    out = []
    if not blind:
        out.append(f"# Parody of \"{spec.title}\"\n")
        out.append("\n".join(f"- {who(s)}" for s in singers))
        out.append(f"- Scenario: {result['scenario_snapshot']['id']} · Names: {cfg['names']} · "
                   f"Chorus: {cfg['chorus']} · Track: {cfg['track']}"
                   + (" · Guidance: none" if cfg.get("guidance") == "none" else "") + "\n")
        if result.get("reference_lyrics"):
            out.append("- Original lyrics supplied as a style reference\n")
    for key in spec.performance_order:
        sec = spec.sections[key]
        part = result["parts"].get(key, {})
        lines = part.get("lines", [])
        if sec.is_chorus:
            author = part.get("author")
            by = ({"fixed": "given", "original": "original"}.get(author) if isinstance(author, str)
                  else f"written by Singer {author}" if author else "")
            head = f"## {sec.label} ({group_label(sec.sung_by, spec.singers)}{', ' + by if by and not blind else ''})"
        elif sec.is_trade:
            head = f"## {sec.label}"
            lines = [f"**Singer {s}:** {l}" if blind or not names[s] else f"**{names[s]}:** {l}"
                     for s, l in zip(sec.trade, lines)]
        else:
            n = names[sec.singer]
            head = f"## {sec.label} ({'Singer ' + str(sec.singer) if blind or not n else n})"
        if not sec.is_chorus and part.get("author") in ("fixed", "original"):
            head += " (given)"
        out.append(head)
        out.append("  \n".join(lines) + "\n")
    if show_scores and not blind:
        sc = result["scores"]
        rows = ["| Singer | Model | Adherence | First-try pass | Retries |", "|---|---|---|---|---|"]
        for s, b in sc["by_singer"].items():
            adh = f"{b['adherence']:.0%}" if b["adherence"] is not None else "–"
            ftp = f"{b['first_try_pass_rate']:.0%}" if b["first_try_pass_rate"] is not None else "–"
            rows.append(f"| {s} | {b['model']} | {adh} | {ftp} | {b['retries']} |")
        out.append("## Scores\n" + "\n".join(rows))
        issues = []
        for key, v in result["verification"].items():
            for e in SectionReport(section=key, lines=[LineReport(**l) for l in v["lines"]],
                                   expected_lines=v["expected_lines"],
                                   structure_errors=v["structure_errors"],
                                   rhyme_errors=v["rhyme_errors"]).errors(GATES):
                issues.append(f"- {spec.sections[key].label}: {e}")
        if issues:
            out.append("\n### Remaining issues\n" + "\n".join(issues))
        if "judge" in result:
            j = result["judge"]
            out.append("\n### Judge (" + j["judge_model"] + ")\n" + "\n".join(
                f"- {k}: {v}" for k, v in j["scores"].items()) + f"\n\n{j.get('notes', '')}")
        u = result["usage"]
        out.append(f"\n_{u['calls']} calls · {u['prompt_tokens'] + u['completion_tokens']:,} tokens"
                   + (f" · ${u['cost']:.4f}" if u.get("cost") else "") + f" · {u['elapsed_s']}s_")
    return "\n".join(out) + "\n"


def save(result: dict, out_dir: str | Path) -> tuple[Path, Path]:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    jp = d / f"{result['id']}.json"
    mp = d / f"{result['id']}.md"
    jp.write_text(json.dumps(result, indent=2))
    mp.write_text(render_sheet(result))
    return jp, mp
