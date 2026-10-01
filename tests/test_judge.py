"""Blind judging: name redaction, prompts, parsing, and pairwise records. Synthetic text only."""

import json

import pytest

from weird_ai_bench.judge import (JUDGE_VERSION, _context, _extract_json, _score, _sheet, check_notes, family_overlap,
                             pairwise, redact_names, rubric, same_family_warning)
from weird_ai_bench.llm import ScriptedClient
from weird_ai_bench.orchestrate import RunConfig, Song, rescore

CHORUS = "<lyrics>We watch the light\nWe walk back home</lyrics>"
OPENING = "<lyrics>The sky is bright</lyrics>"
TAIL = ["<lyrics>You take the road</lyrics>", "<lyrics>I take the train</lyrics>",
        "<lyrics>Now we walk back home</lyrics>"]
MODELS = ["anthropic/claude-sonnet-5", "openai/gpt-5"]
REFERENCE = "You take the road"  # a reference line from two_voices


def make(models=MODELS, **kw) -> dict:
    return Song(RunConfig(models, track="freeform", **kw),
                ScriptedClient([CHORUS, OPENING, *TAIL])).run()


def prompts(client: ScriptedClient) -> list[str]:
    return [c["messages"][0]["content"] for c in client.calls]


def test_version_bumped():
    assert JUDGE_VERSION == 4


def test_redacts_persona_model_and_family_names():
    r = make(names="assigned", personas=["Harbor", "Lantern"])
    text = ("Harbor says hi. lantern's turn. claude-sonnet-5 and anthropic/claude-sonnet-5 "
            "and Claude and Anthropic. GPT-5, ChatGPT's, gpt-5-mini, OpenAI.")
    out = redact_names(text, r)
    assert out == ("Singer 1 says hi. Singer 2's turn. Singer 1 and Singer 1 "
                   "and Singer 1 and Singer 1. Singer 2, Singer 2's, Singer 2, Singer 2.")


def test_redaction_respects_word_boundaries_and_keeps_punctuation():
    r = make()
    out = redact_names("Claudette met GPT. Then claude-sonnet-5.", r)
    assert out == "Claudette met Singer 2. Then Singer 1."


def test_redaction_leaves_singer_labels_alone():
    r = make(names="assigned", personas=["Singer", "Lantern"])
    assert redact_names("Singer 1 and Singer 2's line", r) == "Singer 1 and Singer 2's line"


def test_keep_protects_title_words():
    r = make(["a/one", "b/two"])
    assert redact_names('Two sing "Two Voices".', r) == 'Singer 2 sing "Singer 2 Voices".'
    assert redact_names('Two sing "Two Voices".', r, ("Two Voices",)) == 'Singer 2 sing "Two Voices".'
    assert redact_names('one sings "One Voice".', r, ("One Voice",)) == 'Singer 1 sings "One Voice".'


def test_shared_family_alias_is_not_guessed():
    r = make(["anthropic/claude-sonnet-5", "anthropic/claude-haiku-5"])
    out = redact_names("Claude, claude-haiku-5, and claude-sonnet-5's verse.", r)
    assert out == "a singer, Singer 2, and Singer 1's verse."


def test_same_model_twice_is_ambiguous():
    r = make(["openai/gpt-5", "openai/gpt-5"])
    assert redact_names("gpt-5 wrote it", r) == "a singer wrote it"


def test_persona_clashing_with_other_singers_family_is_ambiguous():
    r = make(["deepseek/deepseek-chat", "openai/gpt-5"], names="assigned", personas=["ChatGPT", "Other"])
    assert redact_names("ChatGPT spoke", r) == "a singer spoke"


def test_blind_prompts_hide_names_and_show_reference():
    lines = ["We watch the light", "We walk back home"]
    r = make(names="assigned", personas=["Harbor", "Lantern"])
    r["parts"]["opening"]["lines"] = ["Harbor, Claude's sky is bright"]
    r["parts"]["exchange"]["lines"] = ["Lantern, you take GPT-5's road", "I take the train"]
    c = ScriptedClient(['{"singability": 7, "humor": 6, "parody_craft": 5, "coherence": 7, '
                        '"interplay": 4, "notes": "ok"}'])
    rubric(r, c, "mistralai/mistral-large")
    (p,) = prompts(c)
    for name in ("Harbor", "Lantern", "claude", "gpt", "anthropic", "openai"):
        assert name not in p.lower()
    assert "Singer 1, Singer 1's sky is bright" in p
    assert "<reference_lyrics>" in p and REFERENCE in p
    assert all(line in p for line in lines)
    assert "deserve no credit" in p

    c = ScriptedClient(['{"winner": 1}', '{"winner": 2}'])
    pairwise(r, r, c, "mistralai/mistral-large")
    for p in prompts(c):
        for name in ("harbor", "lantern", "claude", "gpt", "anthropic", "openai"):
            assert name not in p.lower()
        assert "<reference_lyrics>" in p and "same setup" in p


def test_reference_is_escaped():
    r = make()
    r["spec_snapshot"]["sections"]["opening"]["lines"][0]["reference"] = "The <sky> & bright"
    ctx = _context(r)
    assert "The &lt;sky&gt; &amp; bright" in ctx and "<sky>" not in ctx


def test_no_reference_block_without_reference_lyrics():
    r = make()
    for sec in r["spec_snapshot"]["sections"].values():
        for line in sec["lines"]:
            line["reference"] = None
    assert "<reference_lyrics>" not in _context(r)


def test_setup_text_is_redacted():
    r = make()
    r["scenario_snapshot"]["text"] = "Claude and GPT-5 sing about {title}."
    ctx = _context(r)
    assert "Singer 1 and Singer 2 sing about" in ctx and "Claude" not in ctx


def test_mix_gives_each_song_its_own_setup():
    a = make(scenario="each_other")
    b = make(scenario="none")
    c = ScriptedClient(['{"winner": 1}', '{"winner": 2}'])
    out = pairwise(a, b, c, "mistralai/mistral-large")
    for p in prompts(c):
        assert "same setup" not in p
        assert "SONG 1 was written under this setup" in p and "SONG 2 was written under this setup" in p
    assert "The singers are singing to each other" in prompts(c)[0].split("SONG 2 was written")[0]
    assert "The singers are singing to each other" in prompts(c)[1].split("SONG 2 was written")[1]
    assert out["votes"] == ["a", "a"] and out["winner"] == "a"


def test_pairwise_record():
    a, b = make(), make()
    out = pairwise(a, b, ScriptedClient(['{"winner": 1}', '{"winner": 1}']), "mistralai/mistral-large")
    assert out["votes"] == ["a", "b"] and out["winner"] == "tie" and out["consistent"] is False
    assert out["judge_version"] == JUDGE_VERSION and out["judge"] == "mistralai/mistral-large"
    assert out["score_a"] == 0.5 and out["a"] == a["id"] and out["b"] == b["id"]
    out = pairwise(a, b, ScriptedClient(['{"winner": 2}', '{"winner": 1}']), "mistralai/mistral-large")
    assert out["votes"] == ["b", "b"] and out["consistent"] is True and out["winner"] == "b"
    out = pairwise(a, b, ScriptedClient(['{"winner": 1}', '{"winner": "tie"}']), "mistralai/mistral-large")
    assert out["winner"] == "tie" and out["score_a"] == 0.5


def test_extract_json_ignores_braces_in_prose():
    text = 'I weighed {both songs} carefully.\n{"winner": 2, "reason": "uses {braces}"}\nDone {sic}.'
    assert _extract_json(text) == {"winner": 2, "reason": "uses {braces}"}
    assert _extract_json('{"a": 1} then {"b": {"c": 2}}') == {"b": {"c": 2}}
    assert _extract_json('```json\n{"x": 1}\n```') == {"x": 1}
    with pytest.raises(ValueError):
        _extract_json("no json {here} at all")


def test_rubric_accepts_fractions_and_skips_bad_scores():
    r = make()
    reply = json.dumps({"singability": "8/10", "humor": 7, "parody_craft": "n/a",
                        "coherence": "9 - strong", "interplay": None, "notes": "fine"})
    out = rubric(r, ScriptedClient([reply]), "mistralai/mistral-large")
    s = out["scores"]
    assert s["singability"] == 8 and s["humor"] == 7 and s["coherence"] == 9
    assert "parody_craft" not in s and "interplay" not in s
    assert s["overall"] == 8
    assert _score(True) is None and _score("x") is None and _score(float("nan")) is None


def test_family_overlap_and_warning():
    models = ["anthropic/claude-sonnet-5", "gpt-5", "x-ai/grok-4"]
    assert family_overlap(models, "openai/gpt-5-mini") == ["gpt-5"]
    assert family_overlap(models, "claude-haiku-5") == ["anthropic/claude-sonnet-5"]
    assert family_overlap(models, "google/gemini-3") == []
    r = make(["openai/gpt-5", "x-ai/grok-4"])
    assert "gpt-5" in same_family_warning(r, "gpt-4o")
    assert same_family_warning(r, "google/gemini-3") is None


def test_sheet_lists_automated_check_misses():
    r = make()
    line = r["verification"]["opening"]["lines"][0]
    line.update(syllables_ok=False, count=9, copied=False)
    notes = check_notes(r)
    assert notes.startswith("Automated checks: 5 of 6 generated lines")
    assert f"Opening: line 1 has 9 syllables (target {line['target']})" in notes
    c = ScriptedClient(['{"winner": 1}', '{"winner": 2}'])
    pairwise(r, make(), c, "mistralai/mistral-large")
    assert all(p.count("Automated checks:") == 2 for p in prompts(c))


def test_check_notes_count_unwritten_lines():
    r = make()
    r["verification"]["ending"]["lines"] = []
    r["verification"]["ending"]["structure_errors"] = ["Ending needs exactly 1 lines; got 0."]
    notes = check_notes(r)
    assert "Ending: 1 line never written." in notes and "needs exactly" not in notes
    assert "5 of 6 generated lines" in notes


def test_setup_keeps_assigned_character_names():
    r = make(names="assigned", personas=["Harbor", "Lantern"])
    r["scenario_snapshot"]["text"] = "Singer 1 plays Harbor. Singer 2 plays Lantern."
    assert "Singer 1 plays Harbor. Singer 2 plays Lantern." in _context(r)
    # A persona that is also a singer's model name is still hidden.
    r = make(names="assigned", personas=["GPT", "Lantern"])
    r["scenario_snapshot"]["text"] = "Singer 1 plays GPT."
    assert "plays GPT" not in _context(r)


def test_names_the_setup_gives_everyone_stay_visible():
    r = make(["openai/gpt-5", "openai/gpt-5"])
    r["scenario_snapshot"]["text"] = "Put GPT in the hook."
    r["parts"]["opening"]["lines"] = ["That's GPT, and gpt-5 wrote it"]
    sheet = _sheet(r)
    assert "That's GPT, and a singer wrote it" in sheet


def test_newer_families_are_redacted():
    r = make(["moonshotai/kimi-k3", "z-ai/glm-5"])
    assert redact_names("Kimi and GLM-5 sang", r) == "Singer 1 and Singer 2 sang"
