"""Blind judging: rubric scores per song, and pairwise A-vs-B comparisons."""

from __future__ import annotations

import html
import json
import math
import re

from .llm import display_name, family
from .orchestrate import render_sheet, result_scenario
from .spec import describe_internal_rhyme, result_spec, syllable_map

# Bump when a judge prompt changes; cached judgments from other versions are ignored.
JUDGE_VERSION = 5

CRITERIA = {
    "singability": "Would the lines fit the original melody when sung? Natural word stress, "
                   "no cramming, no filler words added just to hit a count.",
    "humor": "Do the jokes land? Specific, surprising jokes beat generic ones.",
    "parody_craft": "Does it echo the original song's structure, hook, and phrasing cleverly, "
                    "without relying on copied source lines? A repeated hook can be part of the craft.",
    "coherence": "Does each part have a point, and do the sections flow naturally into each other?",
    "interplay": "Do the later parts actually respond to what the "
                 "other singers wrote?",
}


def criteria(result: dict) -> dict[str, str]:
    """A solo song has no one to play off, so it isn't scored on interplay."""
    crit = dict(CRITERIA)
    if len(result["config"]["models"]) == 1:
        del crit["interplay"]
    return crit


def family_overlap(models: list[str], judge_model: str) -> list[str]:
    """The singer models that come from the judge's family, in order, without repeats."""
    fam = family(judge_model)
    return list(dict.fromkeys(m for m in models if family(m) == fam))


def same_family_warning(result: dict, judge_model: str) -> str | None:
    shared = family_overlap(result["config"]["models"], judge_model)
    if shared:
        return (f"judge {judge_model} is from the same family as a singer ({', '.join(shared)}); "
                f"scores may favor its own family's style")
    return None


# What models call themselves, by family (as llm.family names it).
FAMILY_ALIASES = {
    "anthropic": ["Claude", "Anthropic"],
    "openai": ["ChatGPT", "GPT", "OpenAI"],
    "google": ["Gemini", "Gemma", "Google", "Bard"],
    "x-ai": ["Grok", "xAI"],
    "meta-llama": ["Llama", "Meta", "Muse"],
    "deepseek": ["DeepSeek"],
    "mistralai": ["Mistral", "Mixtral"],
    "qwen": ["Qwen"],
    "moonshotai": ["Kimi", "Moonshot"],
    "z-ai": ["GLM", "Zhipu"],
    "xiaomi": ["MiMo", "Xiaomi"],
    "minimax": ["MiniMax"],
}
# Version tails such as "-5", " 4o", "-3.5-turbo", so "GPT-5-mini" goes as one name.
_TAIL = r"(?:[ -]?\d(?:\w|\.(?=\d))*)?(?:-[A-Za-z0-9](?:\w|\.(?=\d))*)*"


def redact_names(text: str, result: dict, keep: tuple[str, ...] = ()) -> str:
    """Replace singer personas, model names, and family names with "Singer N".

    Matching ignores case and respects word boundaries. A name that belongs to more than one
    singer becomes "a singer" rather than a guess, and "Singer N" itself is left alone, as is
    any string in `keep` (the song's title and artist, which may share a word with a model name).
    """
    cfg = result["config"]
    owners: dict[str, tuple[set[int], bool]] = {}  # lowercase name -> (singers, takes a version tail)

    def add(name: str | None, singer: int, tail: bool) -> None:
        if name and len(name.strip()) >= 3:
            key = name.strip().lower()
            who, had_tail = owners.get(key, (set(), False))
            owners[key] = (who | {singer}, had_tail or tail)

    personas = cfg.get("personas") or []
    for i, model in enumerate(cfg["models"], 1):
        if i <= len(personas):
            add(personas[i - 1], i, False)
        for name in (model, display_name(model), *FAMILY_ALIASES.get(family(model), [])):
            add(name, i, True)
    if not owners:
        return text
    names = sorted(owners, key=len, reverse=True)
    alts = "|".join(f"({re.escape(n)}{_TAIL if owners[n][1] else ''})" for n in names)
    # A kept word followed by a version ("GPT" in "GPT-5") is a model name, and still goes.
    kept = "|".join([r"Singer\s+\d+", *(re.escape(k) + r"(?![ -]?\d)"
                                          for k in sorted(keep, key=len, reverse=True) if k)])
    pattern = re.compile(rf"(?<!\w)(?:({kept})|{alts})(['\u2019]s)?(?!\w)", re.I)

    def sub(m: re.Match) -> str:
        if m.group(1):
            return m.group(0)
        i = next(i for i in range(len(names)) if m.group(i + 2) is not None)
        who = owners[names[i]][0]
        return (f"Singer {next(iter(who))}" if len(who) == 1 else "a singer") + (m.group(len(names) + 2) or "")

    return pattern.sub(sub, text)


def _context(result: dict) -> str:
    spec = result_spec(result)
    cfg = result["config"]
    chorus_note = {
        "fixed": "The chorus was given to the singers; they didn't write it. Judge the generated "
                 "sections, and how well they fit with the given chorus.",
        "original": "The chorus is the original song's chorus; the singers didn't write it. Judge "
                    "the generated sections, and how well they fit with it.",
    }.get(cfg["chorus"], "The chorus was generated as part of the song.")
    if spec.chorus_key() is None:
        chorus_note = "This template has no shared chorus; judge all generated sections."
    given = [spec.sections[k].label for k, part in result["parts"].items()
             if part.get("author") in ("fixed", "original")]
    if given:
        chorus_note = ("Prewritten sections supplied to the singers: " + ", ".join(given) +
                       ". Evaluate the generated sections and how they fit with the supplied material. "
                       "Do not credit or penalize the models for writing the supplied sections.")
    scenario = result_scenario(result)
    setup = [scenario.render(spec)]
    setup += [f"Singer {k} was also told: {scenario.singer_text(spec, k)}"
              for k in sorted(scenario.per_singer) if scenario.singer_text(spec, k)]
    # Assigned personas are characters every song in the group shares, so naming them in the setup
    # reveals no model; replacing them would leave "Singer 1 plays Singer 1".
    characters = tuple(p for p in (cfg.get("personas") or [])
                       if p and cfg.get("names") == "assigned" and not _names_a_model(p, result))
    setup = redact_names("\n".join(x for x in setup if x.strip()), result,
                         (spec.title, spec.artist, *characters))
    setup_note = (f"The singers were given this setup:\n<setup>\n{setup}\n</setup>" if setup
                  else "The singers were given no setup beyond the song itself.")
    refrains = []
    for sec in spec.sections.values():
        groups: dict[str, list[int]] = {}
        for i, line in enumerate(sec.lines, 1):
            if line.refrain:
                groups.setdefault(line.refrain, []).append(i)
        refrains.extend(f"{sec.label} lines {', '.join(map(str, idxs))}"
                        for idxs in groups.values() if len(idxs) > 1)
    refrain_note = (
        "These lines are marked as deliberate refrains: " + "; ".join(refrains) +
        ". Repeating their hook phrase or ending is part of the form. Judge whether the "
        "refrain works, rather than treating the repetition itself as a weak rhyme or a flaw.\n\n"
        if refrains else ""
    )
    n = len(cfg["models"])
    internal = [f"{sec.label} line {i}: {describe_internal_rhyme(line.internal_rhyme)}."
                for sec in spec.sections.values() for i, line in enumerate(sec.lines, 1)
                if line.internal_rhyme]
    internal_note = ("Required internal rhymes:\n" + "\n".join(internal) + "\n\n"
                     if internal else "")
    ref = spec.reference_text()
    ref_note = (
        "Here are the original song's lyrics, for judging parody craft. Lines copied from the "
        "original deserve no credit. Section and speaker tags are context only.\n"
        f"<reference_lyrics>\n{html.escape(ref, quote=False)}\n</reference_lyrics>\n\n"
        if ref is not None else ""
    )
    by = "one AI model" if n == 1 else f"{n} AI models"
    return (
        f'This is a parody written by {by} to the tune of "{spec.title}" '
        f"({spec.artist}). {chorus_note}\n\n{setup_note}\n\n{ref_note}{refrain_note}"
        f"Target syllables per line:\n{syllable_map(spec)}\n\n{internal_note}"
        f"You can't hear it, so judge singability from the text, the target counts, and the "
        f"automated check results listed after each song. The checker counts syllables and rhymes "
        f"from a pronouncing dictionary and can be wrong about how a word is sung, so weigh each "
        f"miss by how much it would hurt a real performance. "
        f"Melisma holds one syllable across several notes; it does not add syllables. "
        f"Where explicit prosody settings are supplied, their note spans and stress positions "
        f"are author-provided constraints, not observations of a performance. Count tolerance "
        f"in legacy templates is not evidence of melody fit. Neither reference text nor a "
        f"passing check establishes performed singability. "
        f"Text inside <adlib> tags is an uncounted ad-lib, not part of the main line's meter or rhyme."
    )


def _names_a_model(name: str, result: dict) -> bool:
    """Whether a persona would be redacted as some singer's model or family name anyway."""
    probe = redact_names(name, {**result, "config": {**result["config"], "personas": []}})
    return probe != name


def check_notes(result: dict) -> str:
    """The automated meter, rhyme, and copying misses in the generated sections, as plain text."""
    spec = result_spec(result)
    verification = result.get("verification") or {}
    notes, total, ok = [], 0, 0
    for key in dict.fromkeys(spec.performance_order):
        part = result["parts"].get(key) or {}
        if key not in verification or part.get("author") in ("fixed", "original"):
            continue
        rep, sec = verification[key], spec.sections[key]
        found = []
        for line in rep.get("lines", []):
            total += 1
            ok += bool(line.get("syllables_ok"))
            if not line.get("syllables_ok"):
                lo = max(line["target"] - line.get("under", 0), 1)
                hi = line["target"] + line.get("over", 0)
                need = (" or ".join(map(str, line["allowed_counts"])) if line.get("allowed_counts") else
                        f"{lo} to {hi}" if lo != hi else str(lo))
                found.append(f"line {line['index']} has {line.get('count')} syllables (target {need})")
            if line.get("setting_name") is not None:
                passed = (line.get("syllables_ok") and
                          line.get("stress_hits") == line.get("stress_required") and
                          line.get("split_ok") is not False)
                found.append(f"line {line['index']} evaluated setting '{line['setting_name']}' "
                             f"({'matches declared meter' if passed else 'meter mismatch'})")
            if line.get("syllables_ok"):
                found.extend(f"line {line['index']}: {issue}" for issue in line.get("stress_issues", []))
                if line.get("split_ok") is False:
                    found.append(f"line {line['index']} misses its required phrase boundary")
            if line.get("guessed_words"):
                found.append(f"line {line['index']} uses estimated pronunciations: " +
                             ", ".join(line["guessed_words"]))
            if line.get("copied"):
                found.append(f"line {line['index']} copies the original")
        missing = len(sec.lines) - len(rep.get("lines", []))
        if missing > 0:
            total += missing
            found.append(f"{missing} line{'s' if missing > 1 else ''} never written")
        found += [e.rstrip(".") for e in rep.get("structure_errors", [])
                  if not (missing > 0 and "needs exactly" in e)]
        found += [e.rstrip(".") for e in rep.get("rhyme_errors", [])]
        if found:
            notes.append(f"- {sec.label}: " + "; ".join(found) + ".")
    head = f"Automated checks: {ok} of {total} generated lines are within their syllable targets."
    text = head + ("\n" + "\n".join(notes) if notes else " No other misses.")
    return redact_names(text, result, (spec.title, spec.artist, *scenario_terms(result)))


def _extract_json(text: str) -> dict:
    """The last JSON object in the reply; braces in surrounding prose don't count."""
    dec = json.JSONDecoder()
    text = text or ""
    found = None
    i = text.find("{")
    while i != -1:
        try:
            obj, end = dec.raw_decode(text, i)
        except ValueError:
            i = text.find("{", i + 1)
            continue
        if isinstance(obj, dict):
            found = obj
        i = text.find("{", end)
    if found is None:
        raise ValueError(f"judge returned no JSON: {text[:200]!r}")
    return found


def _score(value) -> float | None:
    """A rubric score from 8, 8.5, "8", or "8/10"; None when there is no usable number."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        out = float(value)
    else:
        m = re.match(r"\s*(\d+(?:\.\d+)?)", value) if isinstance(value, str) else None
        if not m:
            return None
        out = float(m.group(1))
    return out if math.isfinite(out) else None


def scenario_terms(result: dict) -> tuple[str, ...]:
    """Model and family names the setup itself gives every singer, such as a hook built on "GPT".

    Every song in the group was told to use them, so they reveal no author, and replacing them
    in one family's songs only would garble those songs alone.
    """
    sc = result.get("scenario_snapshot") or {}
    setup = " ".join([sc.get("text") or "", *(sc.get("per_singer") or {}).values()])
    names = {n for m in result["config"]["models"]
             for n in (m, display_name(m), *FAMILY_ALIASES.get(family(m), []))}
    return tuple(n for n in names if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", setup, re.I))


def _sheet(result: dict) -> str:
    sheet = redact_names(render_sheet(result, blind=True, show_scores=False), result,
                         scenario_terms(result))
    return f"{sheet}\n\n{check_notes(result)}" if result.get("verification") else sheet


def blend_singability(scores: dict, adherence: dict[str, float]) -> None:
    """Average the judge's singability with the automated meter score, in place."""
    if adherence and "singability" in scores:
        meter = sum(adherence.values()) / len(adherence)
        scores["singability_blended"] = round(0.5 * scores["singability"] + 5.0 * meter, 2)


def rubric(result: dict, client, judge_model: str) -> dict:
    crit = criteria(result)
    sheet = _sheet(result)
    keys = ", ".join(f'"{k}"' for k in crit)
    prompt = (
        f"{_context(result)}\n\nScore the song from 1 to 10 on each criterion:\n"
        + "\n".join(f"- {k}: {v}" for k, v in crit.items())
        + f"\n\nThe song:\n\n{sheet}\n\nReply with JSON only: {{{keys}, \"notes\": "
          f"\"two or three sentences on the strongest and weakest lines\"}}"
    )
    comp = client.complete(judge_model, [{"role": "user", "content": prompt}])
    data = _extract_json(comp.text)
    scores = {k: v for k in crit if (v := _score(data.get(k))) is not None}
    blend_singability(scores, result["scores"]["adherence"])
    main = [scores[k] for k in crit if k in scores]
    scores["overall"] = round(sum(main) / len(main), 2) if main else None
    out = {"judge_model": judge_model, "scores": scores, "notes": data.get("notes", ""),
           "cost": comp.cost}
    warn = same_family_warning(result, judge_model)
    if warn:
        out["warning"] = warn
    return out


def pairwise(a: dict, b: dict, client, judge_model: str) -> dict:
    """Compare two songs twice with positions swapped. Returns winner 'a', 'b', or 'tie'."""
    votes = []
    crit_b = criteria(b)
    weigh = ", ".join(k.replace("_", " ") for k in criteria(a) if k in crit_b)
    for first, second, flip in ((a, b, False), (b, a, True)):
        ctx1, ctx2 = _context(first), _context(second)
        ask = f"Which is the better parody overall, weighing {weigh}?\n\n"
        if ctx1 == ctx2:
            prompt = (f"{ctx1}\n\nHere are two songs written under the same setup. {ask}"
                      f"SONG 1:\n\n{_sheet(first)}\n\nSONG 2:\n\n{_sheet(second)}\n\n")
        else:
            prompt = (f"Here are two songs, each written under its own setup. {ask}"
                      f"SONG 1 was written under this setup:\n\n{ctx1}\n\n"
                      f"SONG 1:\n\n{_sheet(first)}\n\n"
                      f"SONG 2 was written under this setup:\n\n{ctx2}\n\n"
                      f"SONG 2:\n\n{_sheet(second)}\n\n")
        prompt += 'Reply with JSON only: {"winner": 1 or 2 or "tie", "reason": "one sentence"}'
        comp = client.complete(judge_model, [{"role": "user", "content": prompt}])
        data = _extract_json(comp.text)
        w = str(data.get("winner")).strip().lower()
        pick = {"1": "first", "2": "second"}.get(w, "tie")
        if pick == "first":
            votes.append("b" if flip else "a")
        elif pick == "second":
            votes.append("a" if flip else "b")
        else:
            votes.append("tie")
    # Every disagreement, including a win paired with a tie, is a tie.
    score_a = {"a": 1.0, "tie": 0.5, "b": 0.0}[votes[0]] if votes[0] == votes[1] else 0.5
    winner = "a" if score_a > 0.5 else "b" if score_a < 0.5 else "tie"
    return {"a": a["id"], "b": b["id"], "winner": winner, "score_a": score_a,
            "votes": votes, "consistent": votes[0] == votes[1], "judge": judge_model,
            "judge_version": JUDGE_VERSION}
