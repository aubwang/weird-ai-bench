"""Blind judging: rubric scores per song, and pairwise A-vs-B comparisons."""

from __future__ import annotations

import json
import re

from .llm import family
from .orchestrate import render_sheet, result_scenario
from .spec import result_spec, syllable_map

CRITERIA = {
    "singability": "Would the lines fit the original melody when sung? Natural word stress, "
                   "no cramming, no filler words added just to hit a count.",
    "humor": "Do the jokes land? Specific, surprising jokes beat generic ones.",
    "parody_craft": "Does it echo the original song's structure, hook, and phrasing cleverly, "
                    "without just copying lines?",
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


def same_family_warning(result: dict, judge_model: str) -> str | None:
    fams = {family(m) for m in result["config"]["models"]}
    if family(judge_model) in fams:
        return (f"judge {judge_model} is from the same family as a singer; "
                f"scores may favor its own family's style")
    return None


def _context(result: dict) -> str:
    spec = result_spec(result)
    cfg = result["config"]
    chorus_note = {
        "fixed": "The chorus was given to the singers; they didn't write it. Judge the generated "
                 "sections, and how well they fit with the given chorus.",
        "original": "The chorus is the original song's chorus; the singers didn't write it. Judge "
                    "the generated sections, and how well they fit with it.",
    }.get(cfg["chorus"], "The singers wrote the chorus too.")
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
    setup = "\n".join(x for x in setup if x.strip())
    setup_note = (f"The singers were given this setup:\n<setup>\n{setup}\n</setup>" if setup
                  else "The singers were given no setup beyond the song itself.")
    n = len(cfg["models"])
    by = "one AI model" if n == 1 else f"{n} AI models"
    return (
        f'This is a parody written by {by} to the tune of "{spec.title}" '
        f"({spec.artist}). {chorus_note}\n\n{setup_note}\n\n"
        f"Target syllables per line:\n{syllable_map(spec)}\n\n"
        f"You can't hear it, so judge singability from the text and the target counts. "
        f"Text inside <adlib> tags is an uncounted ad-lib, not part of the main line's meter or rhyme."
    )


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", flags=re.S)
    if not m:
        raise ValueError(f"judge returned no JSON: {text[:200]!r}")
    return json.loads(m.group(0))


def rubric(result: dict, client, judge_model: str) -> dict:
    crit = criteria(result)
    sheet = render_sheet(result, blind=True, show_scores=False)
    keys = ", ".join(f'"{k}"' for k in crit)
    prompt = (
        f"{_context(result)}\n\nScore the song from 1 to 10 on each criterion:\n"
        + "\n".join(f"- {k}: {v}" for k, v in crit.items())
        + f"\n\nThe song:\n\n{sheet}\n\nReply with JSON only: {{{keys}, \"notes\": "
          f"\"two or three sentences on the strongest and weakest lines\"}}"
    )
    comp = client.complete(judge_model, [{"role": "user", "content": prompt}])
    data = _extract_json(comp.text)
    scores = {k: float(data[k]) for k in crit if k in data}
    gen = result["scores"]["adherence"]
    if gen and "singability" in scores:
        meter = sum(gen.values()) / len(gen)
        scores["singability_blended"] = round(0.5 * scores["singability"] + 5.0 * meter, 2)
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
    weigh = ", ".join(k.replace("_", " ") for k in criteria(a))
    for first, second, flip in ((a, b, False), (b, a, True)):
        prompt = (
            f"{_context(first)}\n\nHere are two songs written under the same setup. Which is "
            f"the better parody overall, weighing {weigh}?\n\n"
            f"SONG 1:\n\n{render_sheet(first, blind=True, show_scores=False)}\n\n"
            f"SONG 2:\n\n{render_sheet(second, blind=True, show_scores=False)}\n\n"
            f'Reply with JSON only: {{"winner": 1 or 2 or "tie", "reason": "one sentence"}}'
        )
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
    # Disagreement between the two orderings is position bias, so it averages toward a tie.
    score_a = sum({"a": 1.0, "tie": 0.5, "b": 0.0}[v] for v in votes) / len(votes)
    winner = "a" if score_a > 0.5 else "b" if score_a < 0.5 else "tie"
    return {"a": a["id"], "b": b["id"], "winner": winner, "score_a": score_a,
            "votes": votes, "judge": judge_model}
