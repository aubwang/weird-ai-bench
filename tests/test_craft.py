"""Soft source-song devices: shared expectations, no new gates. Synthetic only."""
from copy import deepcopy
from dataclasses import asdict

import pytest

from weird_ai_bench.craft import COHERENCE, PARODY_CRAFT, describe_craft
from weird_ai_bench.judge import CRITERIA, _context, criteria, judge_inputs, pairwise, rubric
from weird_ai_bench.leaderboard import group_key
from weird_ai_bench.llm import ScriptedClient
from weird_ai_bench.orchestrate import RunConfig, Song, rescore
from weird_ai_bench.spec import load_spec, spec_from_dict

NOTE = "The chorus contrasts a shared journey with a homeward return; transform that contrast."
RESPONSES = ["<lyrics>We chase the dawn\nWe head for town</lyrics>",
             "<lyrics>A moon stays high</lyrics>", "<lyrics>Take me along</lyrics>",
             "<lyrics>I'll meet you there</lyrics>", "<lyrics>Now we head for town</lyrics>"]


def run(craft=False, guidance="full", track="freeform"):
    spec = load_spec("two_voices")
    if craft:
        spec.sections[spec.chorus_key()].craft_notes = [NOTE]
    client = ScriptedClient(list(RESPONSES))
    result = Song(RunConfig(["a/one", "b/two"], guidance=guidance, track=track),
                  client, spec=spec).run()
    return spec, client, result


def test_writers_and_judges_share_soft_expectations():
    spec, client, result = run(True)
    writer = client.calls[0]["messages"][0]["content"]
    assert describe_craft(spec) in writer and describe_craft(spec) in _context(result)
    assert PARODY_CRAFT in writer and criteria(result)["parody_craft"] == PARODY_CRAFT
    assert COHERENCE in writer and criteria(result)["coherence"] == COHERENCE
    assert "not a checklist" in PARODY_CRAFT
    assert "other features still carry the recognition" in PARODY_CRAFT
    assert "little parody-craft credit" in PARODY_CRAFT
    assert "No exact phrase" in describe_craft(spec)


def test_notes_do_not_change_scores_or_create_internal_rhyme_gates():
    plain, _, baseline = run()
    annotated, _, result = run(True)
    assert result["scores"] == baseline["scores"]
    assert result["verification"] == baseline["verification"]
    assert result["turns"] == baseline["turns"]
    for key in plain.sections:
        assert annotated.sections[key].lines == plain.sections[key].lines
    assert rescore(result)["scores"] == result["scores"]


def test_notes_survive_snapshots_and_separate_groups_and_judge_inputs():
    spec, _, result = run(True)
    restored = spec_from_dict(asdict(spec))
    assert restored == spec
    assert NOTE in describe_craft(restored)
    _, _, old = run()
    assert group_key(result) != group_key(old)
    assert judge_inputs(result) != judge_inputs(old)


def test_old_snapshots_keep_legacy_criteria():
    spec, _, result = run()
    snapshot = asdict(spec)
    for sec in snapshot["sections"].values():
        sec.pop("craft_notes")
    result["spec_snapshot"] = snapshot
    assert not spec_from_dict(snapshot).uses_craft_guidance
    assert describe_craft(spec_from_dict(snapshot)) == ""
    assert criteria(result) == CRITERIA
    assert "Soft parody-craft guidance" not in _context(result)


def test_unguided_does_not_leak_craft_notes_or_add_hidden_judge_expectations():
    _, plain, baseline = run(guidance="none")
    _, annotated, result = run(True, guidance="none")
    assert annotated.calls == plain.calls
    assert criteria(result) == criteria(baseline) == CRITERIA
    assert _context(result) == _context(baseline)
    assert NOTE not in _context(result)


def test_tracks_have_identical_initial_prompts():
    _, strict, _ = run(True, track="strict")
    _, freeform, _ = run(True)
    assert strict.calls[0] == freeform.calls[0]


@pytest.mark.parametrize("bad", [None, "one note", [""], ["   "], [1], [{}]])
def test_reject_malformed_craft_notes(bad):
    spec = load_spec("two_voices")
    raw = asdict(spec)
    raw["sections"][spec.chorus_key()]["craft_notes"] = bad
    with pytest.raises(ValueError, match="craft_notes"):
        spec_from_dict(raw)


def test_judge_redacts_model_identity_in_notes():
    spec, _, result = run(True)
    updated = deepcopy(result)
    updated["spec_snapshot"]["sections"][spec.chorus_key()]["craft_notes"] = ["a/one uses a returning refrain."]
    assert "a/one" not in _context(updated)
    assert "Singer 1 uses a returning refrain" in _context(updated)


@pytest.mark.parametrize("craft,guidance,expanded", [
    (True, "full", True), (False, "full", False), (True, "none", False),
])
def test_actual_pairwise_and_rubric_prompts_receive_matching_criteria(craft, guidance, expanded):
    _, writer, result = run(craft, guidance=guidance)
    client = ScriptedClient(['{"winner":1}', '{"winner":2}', '{"parody_craft":7,"coherence":6}'])
    pairwise(result, deepcopy(result), client, "j/judge")
    rubric(result, client, "j/judge")
    assert len(client.calls) == 3
    for call in client.calls:
        prompt = call["messages"][0]["content"]
        assert (PARODY_CRAFT in prompt) == expanded
        assert (COHERENCE in prompt) == expanded
    assert (PARODY_CRAFT in writer.calls[0]["messages"][0]["content"]) == expanded


def test_mixed_pair_criteria_stay_with_their_song_when_order_reverses():
    _, _, craft = run(True)
    _, _, legacy = run()
    client = ScriptedClient(['{"winner":1}', '{"winner":2}'])
    pairwise(craft, legacy, client, "j/judge")
    for call, craft_position in zip(client.calls, (1, 2)):
        prompt = call["messages"][0]["content"]
        first = prompt.split("SONG 1 criteria:\n", 1)[1].split("SONG 2 criteria:\n", 1)[0]
        second = prompt.split("SONG 2 criteria:\n", 1)[1].split("SONG 1 was written", 1)[0]
        assert (PARODY_CRAFT in first) == (craft_position == 1)
        assert (PARODY_CRAFT in second) == (craft_position == 2)


def test_craft_definition_changes_invalidate_judge_inputs(monkeypatch):
    _, _, result = run(True)
    before = judge_inputs(result)
    monkeypatch.setattr("weird_ai_bench.judge.PARODY_CRAFT", PARODY_CRAFT + " Clarified criterion.")
    assert judge_inputs(result) != before
