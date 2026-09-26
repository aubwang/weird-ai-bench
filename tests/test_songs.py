"""Song-independent generation, source annotations, and CLI behavior."""

from dataclasses import asdict

import pytest
import yaml

from songbench.cli import main
from songbench.judge import rubric
from songbench.llm import ScriptedClient
from songbench.orchestrate import ConfigError, Duet, RunConfig, render_sheet
from songbench.spec import bundled_specs, load_spec, spec_from_dict


def responses():
    return ["<lyrics>We watch the light\nWe walk back home</lyrics>",
            "<lyrics>The sky is bright</lyrics>",
            "<lyrics>You take the road</lyrics>",
            "<lyrics>I take the train</lyrics>",
            "<lyrics>Now we walk back home</lyrics>"]


def test_second_song_runs_with_source_reference_and_second_line_hook():
    client = ScriptedClient(responses())
    r = Duet(RunConfig("a/one", "b/two", spec="two_voices"), client).run()
    assert r["config"]["chorus"] == "model_1"
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


def test_song_specific_fixed_chorus_is_used(tmp_path):
    lines = ["We watch the light", "We walk back home"]
    preset = tmp_path / "chorus.yaml"
    preset.write_text(yaml.safe_dump({"song": "two_voices", "sections": {"refrain": lines}}))
    client = ScriptedClient(responses()[1:])
    r = Duet(RunConfig("a/one", "b/two", spec="two_voices", presets=[str(preset)]), client).run()
    assert r["config"]["chorus"] == "fixed"
    assert r["parts"]["refrain"]["lines"] == lines
    assert r["scores"]["strict_pass"]
    assert len(client.calls) == 4


def test_explicit_fixed_requires_own_chorus():
    with pytest.raises(ConfigError, match="needs a --preset"):
        Duet(RunConfig("a/one", "b/two", spec="two_voices", chorus="fixed"), ScriptedClient())


def test_original_chorus_can_come_from_annotated_source():
    r = Duet(RunConfig("a/one", "b/two", spec="two_voices", chorus="original"),
             ScriptedClient(responses()[1:])).run()
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
    r = Duet(RunConfig("a/one", "b/two", spec=str(path)), client).run()
    assert r["scores"]["strict_pass"]
    task = client.calls[0]["messages"][-1]["content"]
    assert "Write Call and response line 1" in task
    assert "chorus" not in task.lower()
    assert main(["run", "--model-1", "a/one", "--model-2", "b/two", "--spec", str(path), "--dry-run"]) == 0
    assert task in capsys.readouterr().out
    judge = ScriptedClient(['{"singability": 8, "notes": "ok"}'])
    rubric(r, judge, "c/judge")
    assert "no shared chorus" in judge.calls[0]["messages"][0]["content"]


def test_song_listing_and_generated_chorus_dry_run(capsys):
    assert "two_voices" in bundled_specs()
    assert main(["songs"]) == 0
    assert "two_voices" in capsys.readouterr().out
    assert main(["run", "--model-1", "a/one", "--model-2", "b/two", "--spec", "two_voices", "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "Write the refrain" in output


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
