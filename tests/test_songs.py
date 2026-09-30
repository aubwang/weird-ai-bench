"""Song-independent generation, source annotations, and CLI behavior."""

from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

from songbench.cli import main
from songbench.judge import rubric
from songbench.llm import ScriptedClient
from songbench.orchestrate import ConfigError, Song, RunConfig, render_sheet
from songbench.spec import InternalRhymeSpec, bundled_specs, load_spec, slack_hints, spec_from_dict


def responses():
    # Original lines: copying the reference would fail the originality gate.
    return ["<lyrics>We chase the dawn\nWe head for town</lyrics>",
            "<lyrics>The moon is low</lyrics>",
            "<lyrics>You find the key</lyrics>",
            "<lyrics>I find the door</lyrics>",
            "<lyrics>Now we head for town</lyrics>"]


def given_hook_responses():
    # The ending must end with the supplied hook, but not repeat the source's ending line.
    return responses()[1:-1] + ["<lyrics>So we walk back home</lyrics>"]


def test_second_song_runs_with_source_reference_and_second_line_hook():
    client = ScriptedClient(responses())
    r = Song(RunConfig(["a/one", "b/two"], spec="two_voices"), client).run()
    assert r["config"]["chorus"] == "1"
    assert r["scores"]["strict_pass"]
    assert r["verification"]["ending"]["lines"][0]["hook_ok"]
    assert [c["model"] for c in client.calls] == ["a/one", "a/one", "a/one", "b/two", "b/two"]
    prompt = client.calls[0]["messages"][0]["content"]
    assert "[Refrain - both]" in prompt
    assert "Singer 1: You take the road" in prompt
    assert "Singer 2: I take the train" in prompt
    assert "Write Call and response line 1" in client.calls[2]["messages"][-1]["content"]
    assert "bridge" not in client.calls[2]["messages"][-1]["content"].lower()
    assert r["reference_lyrics"]["sha256"]
    assert render_sheet(r).count("## Refrain") == 2


@pytest.mark.parametrize("singers", [2, 3])
def test_featured_artist_writes_only_their_section(singers):
    sections = {
        "chorus": {"label": "Chorus", "sung_by": [1],
                   "lines": [{"syllables": 4}]},
        "lead": {"label": "Lead Verse", "singer": 1,
                 "lines": [{"syllables": 4}]},
    }
    replies = ["We watch the light", "The sky is bright"]
    if singers == 3:
        sections["second_lead"] = {"singer": 2, "lines": [{"syllables": 4}]}
        replies.append("You take the road")
    sections["guest"] = {"label": "Featured Verse", "singer": singers,
                         "lines": [{"syllables": 4}]}
    replies.append("I take the train")
    spec = spec_from_dict({
        "id": "guest_spot", "title": "Guest Spot", "artist": "Synthetic",
        "singers": singers, "sections": sections,
        "generation_order": list(sections),
        "performance_order": [*sections, "chorus"],
    })
    models = [f"provider/voice-{i}" for i in range(1, singers + 1)]
    client = ScriptedClient([f"<lyrics>{line}</lyrics>" for line in replies])
    result = Song(RunConfig(models, scenario="none"), client, spec=spec).run()
    assert result["scores"]["strict_pass"]
    assert [call["model"] for call in client.calls] == [models[0], *models]
    assert result["parts"]["guest"]["author"] == singers
    assert result["parts"]["chorus"]["author"] == 1
    guest_context = "\n".join(m["content"] for m in client.calls[-1]["messages"])
    assert "We watch the light" in guest_context
    assert "The sky is bright" in guest_context
    assert render_sheet(result).count("## Chorus") == 2


def test_targeted_internal_rhyme_survives_snapshot_and_retries(tmp_path):
    raw = {"id": "acronym_hook", "title": "Letter Game", "artist": "Synthetic",
           "singers": 1, "generation_order": ["hook"], "performance_order": ["hook", "hook"],
           "sections": {"hook": {"sung_by": [1], "lines": [{"syllables": 8, "hook": True,
                        "internal_rhyme": {"word_syllables": 3, "end_word": True}}]}}}
    path = tmp_path / "song.yaml"
    path.write_text(yaml.safe_dump(raw))
    client = ScriptedClient(["<lyrics>See the bright light then GPT</lyrics>",
                             "<lyrics>Try GPT then LLC</lyrics>"])
    result = Song(RunConfig(["a/one"], spec=str(path), scenario="none"), client).run()
    assert result["scores"]["strict_pass"]
    assert len(client.calls) == 2
    assert result["turns"][0]["retries"] == 1
    restored = spec_from_dict(result["spec_snapshot"])
    assert restored.sections["hook"].lines[0].internal_rhyme == InternalRhymeSpec(3, True)
    judge = ScriptedClient(['{"singability": 8, "notes": "ok"}'])
    rubric(result, judge, "b/judge")
    assert "3-syllable words or acronyms" in judge.calls[0]["messages"][0]["content"]


@pytest.mark.parametrize("rule", ["yes", 3, {"word_syllables": 0}, {"word_syllables": True},
                                  {"word_syllables": 2.5}, {"end_word": "yes"}, {"typo": 3}])
def test_invalid_internal_rhyme_rules(rule):
    raw = asdict(load_spec("two_voices"))
    raw["sections"]["opening"]["lines"][0]["internal_rhyme"] = rule
    with pytest.raises(ValueError, match="internal_rhyme"):
        spec_from_dict(raw)


def test_song_specific_fixed_chorus_is_used(tmp_path):
    lines = ["We watch the light", "We walk back home"]
    preset = tmp_path / "chorus.yaml"
    preset.write_text(yaml.safe_dump({"song": "two_voices", "sections": {"refrain": lines}}))
    client = ScriptedClient(given_hook_responses())
    r = Song(RunConfig(["a/one", "b/two"], spec="two_voices", presets=[str(preset)]), client).run()
    assert r["config"]["chorus"] == "fixed"
    assert r["parts"]["refrain"]["lines"] == lines
    assert r["scores"]["strict_pass"]
    assert len(client.calls) == 4


def test_explicit_fixed_requires_own_chorus():
    with pytest.raises(ConfigError, match="needs a --preset"):
        Song(RunConfig(["a/one", "b/two"], spec="two_voices", chorus="fixed"), ScriptedClient())


def test_original_chorus_can_come_from_annotated_source():
    r = Song(RunConfig(["a/one", "b/two"], spec="two_voices", chorus="original"),
             ScriptedClient(given_hook_responses())).run()
    assert r["parts"]["refrain"]["lines"] == ["We watch the light", "We walk back home"]
    assert r["scores"]["strict_pass"]




def chorusless_spec():
    raw = asdict(load_spec("two_voices"))
    raw["id"] = "no_chorus"
    raw["sections"] = {k: raw["sections"][k] for k in ("exchange", "opening")}
    raw["generation_order"] = raw["performance_order"] = ["exchange", "opening"]
    return spec_from_dict(raw)


def test_chorusless_song_starts_with_traded_lines(tmp_path, capsys):
    spec = chorusless_spec()
    path = tmp_path / "song.yaml"
    path.write_text(yaml.safe_dump(asdict(spec)))
    client = ScriptedClient(responses()[2:4] + responses()[1:2])
    r = Song(RunConfig(["a/one", "b/two"], spec=str(path)), client).run()
    assert r["scores"]["strict_pass"]
    task = client.calls[0]["messages"][-1]["content"]
    assert "Write Call and response line 1" in task
    assert "chorus" not in task.lower()
    assert main(["run", "--model", "a/one", "--model", "b/two", "--spec", str(path), "--dry-run"]) == 0
    assert task in capsys.readouterr().out
    judge = ScriptedClient(['{"singability": 8, "notes": "ok"}'])
    rubric(r, judge, "c/judge")
    assert "no shared chorus" in judge.calls[0]["messages"][0]["content"]


def test_song_listing_and_generated_chorus_dry_run(capsys):
    assert "two_voices" in bundled_specs()
    assert main(["songs"]) == 0
    assert "two_voices" in capsys.readouterr().out
    assert main(["run", "--model", "a/one", "--model", "b/two", "--spec", "two_voices", "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "Write the refrain" in output


def test_check_uses_marked_hook_in_example(capsys):
    example = Path(__file__).resolve().parents[1] / "examples" / "two_voices.txt"
    assert main(["check", str(example)]) == 0
    assert "Issues:" not in capsys.readouterr().out


@pytest.mark.parametrize("mutation", ["duplicate_order", "missing_section", "invalid_singer", "invalid_trade", "empty_lines"])
def test_invalid_templates_fail_before_generation(mutation):
    raw = asdict(load_spec("two_voices"))
    if mutation == "duplicate_order":
        raw["generation_order"].append("opening")
    elif mutation == "missing_section":
        raw["performance_order"].remove("ending")
    elif mutation == "invalid_singer":
        raw["sections"]["opening"]["singer"] = 3
    elif mutation == "invalid_trade":
        raw["sections"]["exchange"]["trade"] = [1, 3]
    else:
        raw["sections"]["opening"]["lines"] = []
    with pytest.raises(ValueError):
        spec_from_dict(raw)


def test_slack_hints_and_validation(tmp_path):
    spec = load_spec("two_voices")
    assert slack_hints(spec) == []
    assert slack_hints(spec, min_lines=1) == [
        "Opening and Ending differ by up to 1 syllable on line 1. If they share a melody, "
        "consider `slack` there."]
    spec.sections["ending"].lines[0].slack = 1
    assert slack_hints(spec, min_lines=1) == []
    raw = asdict(load_spec("two_voices"))
    raw["sections"]["opening"]["lines"][0]["slack"] = -1
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="slack"):
        load_spec(str(path))
