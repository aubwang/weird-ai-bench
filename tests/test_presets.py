"""Presets work for any complete section and do not earn model credit."""

import json
from dataclasses import asdict

import pytest
import yaml

from songbench.cli import main
from songbench.judge import rubric
from songbench.leaderboard import group_key
from songbench.llm import ScriptedClient
from songbench.orchestrate import ConfigError, Song, RunConfig, save
from songbench.spec import load_preset, load_spec


def preset_file(tmp_path, sections, song="two_voices", name="preset.yaml"):
    path = tmp_path / name
    path.write_text(yaml.safe_dump({"song": song, "sections": sections}))
    return path


GIVEN = {"opening": [{"text": "The sky is bright", "adlibs": ["oh"]}],
         "exchange": ["You take the road", "I take the train"]}
RESPONSES = ["<lyrics>We watch the light\nWe walk back home</lyrics>",
             "<lyrics>Now we walk back home</lyrics>"]


def test_prewritten_solo_and_traded_sections_are_context_not_model_output(tmp_path):
    path = preset_file(tmp_path, GIVEN)
    client = ScriptedClient(list(RESPONSES))
    duet = Song(RunConfig(["a/one", "b/two"], spec="two_voices", presets=[str(path)]), client)
    path.unlink()
    r = duet.run()
    assert r["scores"]["strict_pass"]
    assert [t["section"] for t in r["turns"]] == ["refrain", "ending"]
    assert set(r["scores"]["adherence"]) == {"refrain", "ending"}
    assert r["parts"]["opening"]["author"] == r["parts"]["exchange"]["author"] == "fixed"
    assert "The sky is bright <adlib>oh</adlib>" in client.calls[0]["messages"][-1]["content"]
    assert "Singer 2 (two): I take the train" in client.calls[0]["messages"][-1]["content"]
    assert r["verification"]["opening"]["lines"][0]["count"] == 4
    assert r["scores"]["by_singer"]["1"]["turns"] == 1
    jp, _ = save(r, tmp_path)
    assert group_key(r) == group_key(json.loads(jp.read_text()))
    judge = ScriptedClient(['{"singability": 8, "notes": "ok"}'])
    rubric(r, judge, "c/judge")
    prompt = judge.calls[0]["messages"][0]["content"]
    assert "Prewritten sections supplied to the singers: Opening, Call and response" in prompt


def test_multiple_presets_compose_and_cli_dry_run_matches(tmp_path, capsys):
    first = preset_file(tmp_path, {"opening": GIVEN["opening"]})
    second = preset_file(tmp_path, {"exchange": GIVEN["exchange"]}, name="other.yaml")
    client = ScriptedClient(list(RESPONSES))
    cfg = RunConfig(["a/one", "b/two"], spec="two_voices", presets=[str(first), str(second)])
    r = Song(cfg, client).run()
    assert len(r["turns"]) == 2
    assert main(["run", "--model", "a/one", "--model", "b/two", "--spec", "two_voices",
                 "--preset", str(first), "--preset", str(second), "--dry-run"]) == 0
    assert client.calls[0]["messages"][-1]["content"] in capsys.readouterr().out


@pytest.mark.parametrize("case", ["song", "section", "length", "duplicate", "chorus_conflict"])
def test_bad_presets_fail_before_calls(tmp_path, case):
    sections = {"opening": ["The sky is bright"]}
    song, chorus = "two_voices", "auto"
    if case == "song":
        song = "another_song"
    if case == "section":
        sections = {"missing": ["A line"]}
    if case == "length":
        sections["opening"].append("Extra line")
    if case == "chorus_conflict":
        sections = {"refrain": ["We watch the light", "We walk back home"]}
        chorus = "2"
    path = preset_file(tmp_path, sections, song=song)
    paths = [str(path)] * (2 if case == "duplicate" else 1)
    client = ScriptedClient()
    with pytest.raises(ConfigError):
        Song(RunConfig(["a/one", "b/two"], spec="two_voices", chorus=chorus, presets=paths), client)
    assert client.calls == []


def test_grouping_uses_supplied_content_not_preset_path(tmp_path):
    def run(path):
        return Song(RunConfig(["a/one", "b/two"], spec="two_voices", track="freeform", presets=[str(path)]),
                    ScriptedClient()).run()
    a = preset_file(tmp_path, GIVEN)
    b = preset_file(tmp_path, GIVEN, name="copy.yaml")
    first = run(a)
    assert group_key(first) == group_key(run(b))
    b = preset_file(tmp_path, {"opening": ["We watch the light"], "exchange": GIVEN["exchange"]}, name="copy.yaml")
    assert group_key(first) != group_key(run(b))


def test_bundled_preset_is_separate_from_song():
    spec = asdict(load_spec())
    assert "fixed_chorus" not in spec
    preset = load_preset("two_voices_seed")
    assert preset["song"] == spec["id"]
    assert preset["sections"]["opening"][0] == "The sky is bright <adlib>oh</adlib>"


def test_all_sections_may_be_prewritten(tmp_path):
    sections = {**GIVEN, "refrain": ["We watch the light", "We walk back home"],
                "ending": ["Now we walk back home"]}
    path = preset_file(tmp_path, sections)
    client = ScriptedClient()
    r = Song(RunConfig(["a/one", "b/two"], spec="two_voices", presets=[str(path)]), client).run()
    assert client.calls == []
    assert r["scores"]["adherence"] == {}
    assert all(v["adherence"] is None for v in r["scores"]["by_singer"].values())
