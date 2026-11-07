"""Blind judging: rubric scores per song, and pairwise A-vs-B comparisons."""

from __future__ import annotations

import html
import json
import math
import re

from .llm import LLMError, display_name, family
from .craft import COHERENCE, PARODY_CRAFT, describe_craft
from .orchestrate import render_sheet, result_scenario
from .spec import describe_internal_rhyme, result_spec, syllable_map

# Bump when prompts or verdict interpretation change; older caches are ignored.
JUDGE_VERSION = 9

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
    if result_spec(result).uses_craft_guidance and result["config"].get("guidance", "full") == "full":
        crit.update(parody_craft=PARODY_CRAFT, coherence=COHERENCE)
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


NEUTRAL_NAME = "[AI name]"


def redact_names(text: str, result: dict, keep: tuple[str, ...] = (),
                 pair: tuple[str, ...] | None = None) -> str:
    """Replace singer personas, model names, and family names with "Singer N".

    Matching ignores case and respects word boundaries. A name that belongs to more than one
    singer becomes "a singer" rather than a guess, and "Singer N" itself is left alone, as is
    any string in `keep` (the song's title and artist, which may share a word with a model name).

    `pair` is every model in both songs of a pairwise comparison. Then company and product
    names ("Google", "ChatGPT") of any family in the pair become NEUTRAL_NAME in both songs, so
    a word means the same thing on both sides: redacting "Google" only in Google's own song
    would garble that song alone and hint at who wrote it. Personas and exact model names still
    become "Singer N".
    """
    cfg = result["config"]
    owners: dict[str, tuple[set[int], bool]] = {}  # lowercase name -> (singers, takes a version tail)
    neutral: set[str] = set()
    if pair is not None:
        for model in pair:
            neutral.update(a.lower() for a in FAMILY_ALIASES.get(family(model), []))
            if not any(model == m for m in cfg["models"]):  # the other song's exact model names
                neutral.update(n.lower() for n in (model, display_name(model)) if len(n) >= 3)

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
            if name.lower() not in neutral:
                add(name, i, True)
    for name in neutral:
        if name not in owners:
            owners[name] = (set(), True)  # no singer: NEUTRAL_NAME
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
        label = (NEUTRAL_NAME if not who else f"Singer {next(iter(who))}" if len(who) == 1
                 else "a singer")
        return label + (m.group(len(names) + 2) or "")

    return pattern.sub(sub, text)


def _context(result: dict, pair: tuple[str, ...] | None = None) -> str:
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
    # Names the setup itself gives every singer stay, as they do in the lyric sheet:
    # redacting them only for their own family's songs would garble those setups and
    # reveal who wrote them.
    kept = (spec.title, spec.artist, *characters, *scenario_terms(result, pair))
    setup = redact_names("\n".join(x for x in setup if x.strip()), result, kept, pair)
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
    craft_note = ""
    if cfg.get("guidance", "full") == "full" and spec.uses_craft_guidance:
        craft_note = redact_names(describe_craft(spec), result, kept, pair) + "\n\n"
    ref = spec.reference_text()
    ref_note = (
        "Here are the original song's lyrics, for judging parody craft. Lines copied from the "
        "original deserve no credit. Section and speaker tags are context only.\n"
        f"<reference_lyrics>\n{html.escape(ref, quote=False)}\n</reference_lyrics>\n\n"
        if ref is not None else ""
    )
    by = "one AI model" if n == 1 else f"{n} AI models"
    settings_note = ("Where a line lists settings, any one of them fits; a syllable held over "
                     "several notes is still one syllable. " if spec.uses_prosody else "")
    if any(p.rhythm for sec in spec.sections.values() for line in sec.lines for p in line.prosody):
        settings_note += ("Timing maps use quarter-note beats, zero-based onsets and one list of "
                          "note durations per syllable; gaps are rests. They describe the target "
                          "rhythm, not evidence of an actual sung performance. ")
    return (
        f'This is a parody written by {by} to the tune of "{spec.title}" '
        f"({spec.artist}). {chorus_note}\n\n{setup_note}\n\n{ref_note}{refrain_note}"
        f"{craft_note}Target syllables per line:\n{syllable_map(spec)}\n\n{internal_note}"
        f"You can't hear it, so judge singability from the text, the target counts, and the "
        f"automated check results listed after each song. The checker counts syllables and rhymes "
        f"from a pronouncing dictionary and can be wrong about how a word is sung, so weigh each "
        f"miss by how much it would hurt a real performance. {settings_note}"
        f"Text inside <adlib> tags is an uncounted ad-lib, not part of the main line's meter or rhyme."
    )


def _names_a_model(name: str, result: dict) -> bool:
    """Whether a persona would be redacted as some singer's model or family name anyway."""
    probe = redact_names(name, {**result, "config": {**result["config"], "personas": []}})
    return probe != name


def check_notes(result: dict, pair: tuple[str, ...] | None = None) -> str:
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
            if line.get("syllables_ok"):
                found.extend(f"line {line['index']}: {issue}" for issue in line.get("stress_issues", []))
                if line.get("split_ok") is False:
                    kind = "word boundary at its phrase break" if line.get("split_mode") == "word" else "pause"
                    found.append(f"line {line['index']} is missing its {kind}")
            if line.get("guessed_words"):
                found.append(f"line {line['index']} has guessed pronunciations: " +
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
    return redact_names(text, result, (spec.title, spec.artist, *scenario_terms(result, pair)), pair)


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


def scenario_terms(result: dict, pair: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """Model and family names the setup itself gives every singer, such as a hook built on "GPT".

    Every song in the group was told to use them, so they reveal no author, and replacing them
    in one family's songs only would garble those songs alone. In a pair, names of the other
    song's models count too, since pair redaction would otherwise replace them.
    """
    sc = result.get("scenario_snapshot") or {}
    setup = " ".join([sc.get("text") or "", *(sc.get("per_singer") or {}).values()])
    names = {n for m in {*result["config"]["models"], *(pair or ())}
             for n in (m, display_name(m), *FAMILY_ALIASES.get(family(m), []))}
    return tuple(n for n in names if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", setup, re.I))


def judge_inputs(result: dict, pair: tuple[str, ...] | None = None) -> list:
    """Everything the judge sees about one song, for cache keys.

    In a pairwise comparison, what the judge sees depends on the other song's models too
    (see redact_names), so pass `pair`: songs whose text doesn't change keep their old key.
    """
    # Pairwise prompts include the criteria's definitions, not just their names.
    return [_context(result, pair), _sheet(result, pair), criteria(result)]


def _sheet(result: dict, pair: tuple[str, ...] | None = None) -> str:
    sheet = redact_names(render_sheet(result, blind=True, show_scores=False), result,
                         scenario_terms(result, pair), pair)
    return f"{sheet}\n\n{check_notes(result, pair)}" if result.get("verification") else sheet


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


_VOTE = {"a": 1.0, "tie": 0.5, "b": 0.0}


def score_from_votes(votes: list[str]) -> float:
    """Song a's score from its two orders: the average, except that opposite wins are a tie.

    a + a is 1, a + tie is 0.75, a + b (the verdict flipped with the order) is 0.5. A win in
    one order and a tie in the other still leans toward the winner; only a full reversal
    carries no preference.
    """
    if {votes[0], votes[1]} == {"a", "b"}:
        return 0.5
    return (_VOTE[votes[0]] + _VOTE[votes[1]]) / 2


def pair_models(a: dict, b: dict) -> tuple[str, ...]:
    """Every model in either song, in a fixed order, for pair-symmetric redaction."""
    return tuple(sorted({*a["config"]["models"], *b["config"]["models"]}))


def pairwise(a: dict, b: dict, client, judge_model: str) -> dict:
    """Compare both orders; an invalid or failed response leaves the pair unresolved."""
    votes = []
    responses = []
    api_failed = False
    crit_b = criteria(b)
    weigh = ", ".join(k.replace("_", " ") for k in criteria(a) if k in crit_b)
    pair = pair_models(a, b)
    for first, second, flip in ((a, b, False), (b, a, True)):
        ctx1, ctx2 = _context(first, pair), _context(second, pair)
        ask = (f"Which is the better parody overall, weighing {weigh}? Weigh them together "
               "into one overall verdict; no single criterion decides it.\n\n")
        # Every judge gets the same definitions, so judges differ in taste, not in what
        # they think the criteria mean.
        crit1, crit2 = criteria(first), criteria(second)
        shared = [k for k in crit1 if k in crit2]
        definitions = lambda c: "\n".join(f"- {k.replace('_', ' ')}: {c[k]}" for k in shared)
        if all(crit1[k] == crit2[k] for k in shared):
            ask += "Judge using these definitions:\n" + definitions(crit1) + "\n\n"
        else:
            # --mix may compare writers given different expectations. Keep
            # each definition attached to its own song in both orientations.
            ask += ("Each song had its own stated criteria.\n"
                    "SONG 1 criteria:\n" + definitions(crit1) + "\n\n"
                    "SONG 2 criteria:\n" + definitions(crit2) + "\n\n")
        shared = 0  # characters every pair in this group sends identically, for caching
        if ctx1 == ctx2:
            prompt = f"{ctx1}\n\nHere are two songs written under the same setup. {ask}"
            shared = len(prompt)
            prompt += f"SONG 1:\n\n{_sheet(first, pair)}\n\nSONG 2:\n\n{_sheet(second, pair)}\n\n"
        else:
            prompt = (f"Here are two songs, each written under its own setup. {ask}"
                      f"SONG 1 was written under this setup:\n\n{ctx1}\n\n"
                      f"SONG 1:\n\n{_sheet(first, pair)}\n\n"
                      f"SONG 2 was written under this setup:\n\n{ctx2}\n\n"
                      f"SONG 2:\n\n{_sheet(second, pair)}\n\n")
        prompt += 'Reply with JSON only: {"winner": 1 or 2 or "tie", "reason": "one sentence"}'
        response = {"order": [first["id"], second["id"]], "raw_text": None,
                    "reason": None, "cost": None, "error": None, "error_kind": None,
                    "model": None, "prompt_tokens": None, "completion_tokens": None,
                    "latency_s": None, "finish_reason": None, "attempted": False}
        if api_failed:
            responses.append(response)
            votes.append(None)
            continue
        response["attempted"] = True
        vote = None
        try:
            message = {"role": "user", "content": prompt}
            if shared:
                message["cache_prefix"] = shared
            comp = client.complete(judge_model, [message])
        except LLMError as exc:
            response["error"] = str(exc)
            response["error_kind"] = "api"
            api_failed = True
        else:
            response.update(raw_text=comp.text, cost=comp.cost,
                            model=comp.model, prompt_tokens=comp.prompt_tokens,
                            completion_tokens=comp.completion_tokens,
                            latency_s=comp.latency_s, finish_reason=comp.raw_finish)
            try:
                data = _extract_json(comp.text)
                response["reason"] = data.get("reason")
                winner = data.get("winner")
                # Reject booleans, floats, and invented labels rather than making up a tie.
                if type(winner) is int and winner in (1, 2):
                    vote = ("b" if flip else "a") if winner == 1 else ("a" if flip else "b")
                elif isinstance(winner, str) and winner.strip().lower() == "tie":
                    vote = "tie"
                else:
                    raise ValueError("winner must be the integer 1, integer 2, or 'tie'")
            except ValueError as exc:
                response["error"] = str(exc)
                response["error_kind"] = "verdict"
        responses.append(response)
        votes.append(vote)
    resolved = all(v is not None for v in votes)
    score_a = score_from_votes(votes) if resolved else None
    winner = ("a" if score_a > 0.5 else "b" if score_a < 0.5 else "tie") if resolved else None
    return {"a": a["id"], "b": b["id"], "winner": winner, "score_a": score_a,
            "status": "resolved" if resolved else "unresolved", "responses": responses,
            "known_cost": sum(r["cost"] for r in responses if r["cost"] is not None),
            "missing_cost_calls": sum(r["attempted"] and r["cost"] is None for r in responses),
            "votes": votes, "consistent": votes[0] == votes[1] if resolved else None, "judge": judge_model,
            "judge_version": JUDGE_VERSION}
