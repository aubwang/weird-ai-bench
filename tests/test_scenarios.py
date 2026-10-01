"""Scenario files carry the framing; the runner adds only the cast and the mechanics."""

import pytest
import yaml

from weird_ai_bench.cli import main
from weird_ai_bench.judge import rubric
from weird_ai_bench.leaderboard import group_key
from weird_ai_bench.llm import ScriptedClient
from weird_ai_bench.orchestrate import ConfigError, RunConfig, Song
from weird_ai_bench.scenario import bundled_scenarios, load_scenario


def scenario_file(tmp_path, name="scenario.yaml", **fields):
    raw = {"id": "custom", "text": 'A roast set to "{title}" by {artist}, for {singers} singers.', **fields}
    path = tmp_path / name
    path.write_text(yaml.safe_dump(raw))
    return str(path)


def test_bundled_scenarios():
    assert {"none", "each_other"} <= set(bundled_scenarios())
    assert load_scenario("each_other").requires_names
    with pytest.raises(ValueError, match="no bundled scenario"):
        load_scenario("missing")


def test_scenario_text_replaces_the_built_in_framing(tmp_path):
    path = scenario_file(tmp_path, per_singer={2: "You are the straight man."})
    song = Song(RunConfig(["a/one", "b/two"], scenario=path), ScriptedClient())
    first, second = song.threads[1][0]["content"], song.threads[2][0]["content"]
    assert first.startswith('A roast set to "Two Voices (example)" by weird ai bench, for 2 singers.')
    assert "straight man" in second and "straight man" not in first
    assert "AI model" not in first and "duet" not in first


def test_scenario_limits_and_names(tmp_path):
    with pytest.raises(ConfigError, match="for 3 to 4 singers"):
        Song(RunConfig(["a/one", "b/two"], scenario=scenario_file(tmp_path, min_singers=3, max_singers=4)),
             ScriptedClient())
    with pytest.raises(ConfigError, match="anonymous"):
        Song(RunConfig(["a/one", "b/two"], names="anonymous"), ScriptedClient())
    song = Song(RunConfig(["a/one", "b/two"], names="anonymous", scenario="none"), ScriptedClient())
    assert "There are 2 singers, and they're unnamed. You are Singer 1." in song.threads[1][0]["content"]


@pytest.mark.parametrize("fields,message", [
    ({"mode": "old"}, "unknown scenario fields"),
    ({"per_singer": {"two": "x"}}, "singer numbers"),
    ({"min_singers": 3, "max_singers": 2}, "singer limits"),
    ({"max_singers": 2, "per_singer": {3: "x"}}, "outside"),
])
def test_invalid_scenarios(tmp_path, fields, message):
    with pytest.raises(ValueError, match=message):
        load_scenario(scenario_file(tmp_path, **fields))


def test_grouping_uses_scenario_text_not_id_or_path(tmp_path):
    def run(path):
        return Song(RunConfig(["a/one", "b/two"], scenario=path, track="freeform"), ScriptedClient()).run()
    first = run(scenario_file(tmp_path))
    assert group_key(first) == group_key(run(scenario_file(tmp_path, "renamed.yaml", id="renamed")))
    assert group_key(first) != group_key(run(scenario_file(tmp_path, "other.yaml", text="Something else.")))


def test_judge_sees_the_setup(tmp_path):
    path = scenario_file(tmp_path, per_singer={2: "You are the straight man."})
    r = Song(RunConfig(["a/one", "b/two"], scenario=path, track="freeform"), ScriptedClient()).run()
    judge = ScriptedClient(['{"singability": 8, "notes": "ok"}'])
    rubric(r, judge, "c/judge")
    prompt = judge.calls[0]["messages"][0]["content"]
    assert 'A roast set to "Two Voices (example)"' in prompt
    assert "Singer 2 was also told: You are the straight man." in prompt


def test_scenarios_listing(capsys):
    assert main(["scenarios"]) == 0
    assert "each_other (2 to any singers)" in capsys.readouterr().out
