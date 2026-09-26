"""Songs for any number of singers, from a solo to a larger cast."""

import json
from collections import Counter

import pytest
import yaml

from songbench.cli import lineups, main
from songbench.judge import rubric
from songbench.leaderboard import group_key
from songbench.llm import ScriptedClient
from songbench.orchestrate import ConfigError, RunConfig, Song, render_sheet
from songbench.spec import spec_from_dict


def trio_raw():
    return {
        "id": "trio", "title": "Trio", "artist": "synthetic", "singers": 3,
        "generation_order": ["hook", "one", "round"],
        "performance_order": ["one", "hook", "round", "hook"],
        "sections": {
            "hook": {"label": "Hook", "sung_by": [2, 3],
                     "lines": [{"syllables": 4, "reference": "We walk back home", "hook": True}]},
            "one": {"label": "Opening", "singer": 1,
                    "lines": [{"syllables": 4, "reference": "The sky is bright"}]},
            "round": {"label": "Round", "trade": [3, 1, 2],
                      "lines": [{"syllables": 4}, {"syllables": 4}, {"syllables": 4}]},
        },
    }


def solo_raw():
    return {
        "id": "solo", "title": "Solo", "artist": "synthetic", "singers": 1,
        "generation_order": ["refrain", "verse"], "performance_order": ["verse", "refrain"],
        "sections": {
            "refrain": {"label": "Refrain", "sung_by": "all", "lines": [{"syllables": 4, "hook": True}]},
            "verse": {"label": "Verse", "singer": 1, "lines": [{"syllables": 4}]},
        },
    }


def write(tmp_path, raw, name="song.yaml"):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(raw))
    return str(path)


TRIO = ["<lyrics>We walk back home</lyrics>", "<lyrics>The sky is bright</lyrics>",
        "<lyrics>You take the road</lyrics>", "<lyrics>I take the train</lyrics>",
        "<lyrics>We take the bus</lyrics>"]
MODELS = ["a/one", "b/two", "c/three"]


def test_three_singers_take_their_own_turns(tmp_path):
    client = ScriptedClient(list(TRIO))
    r = Song(RunConfig(MODELS, spec=write(tmp_path, trio_raw())), client).run()
    assert r["scores"]["strict_pass"]
    assert [c["model"] for c in client.calls] == ["b/two", "a/one", "c/three", "a/one", "b/two"]
    assert r["config"]["chorus"] == "2"
    assert r["parts"]["round"]["author"] == [3, 1, 2]
    assert set(r["scores"]["by_singer"]) == {"1", "2", "3"}
    assert all(b["turns"] for b in r["scores"]["by_singer"].values())

    system = r["threads"]["3"][0]["content"]
    assert "Singer 1 is one, Singer 2 is two, and Singer 3 is three." in system
    assert "You are Singer 3, three" in system
    assert "The other singers write their own parts" in system
    assert "[Hook - Singers 2 and 3]" in system
    assert "sung by Singers 2 and 3, so it isn't only your voice" in client.calls[0]["messages"][-1]["content"]
    # Each singer sees the others' final lines in the song so far.
    assert "Singer 3 (three): You take the road" in client.calls[3]["messages"][-1]["content"]

    sheet = render_sheet(r)
    assert "Singer 3: three (c/three)" in sheet and "## Hook (Singers 2 and 3, written by Singer 2)" in sheet
    assert "c/three" not in render_sheet(r, blind=True)
    judge = ScriptedClient(['{"singability":8,"humor":7,"parody_craft":7,"coherence":8,"interplay":9,"notes":"ok"}'])
    rubric(r, judge, "d/judge")
    assert "written by 3 AI models" in judge.calls[0]["messages"][0]["content"]


def test_lineup_must_match_the_song(tmp_path):
    spec = write(tmp_path, trio_raw())
    with pytest.raises(ConfigError, match="has 3 singers; got 2 models"):
        Song(RunConfig(MODELS[:2], spec=spec), ScriptedClient())
    with pytest.raises(ConfigError, match="doesn't sing"):
        Song(RunConfig(MODELS, spec=spec, chorus="1"), ScriptedClient())
    with pytest.raises(ConfigError, match="one persona per singer"):
        Song(RunConfig(MODELS, spec=spec, names="assigned", personas=["X", "Y"]), ScriptedClient())
    client = ScriptedClient(list(TRIO))
    Song(RunConfig(MODELS, spec=spec, chorus="3"), client).run()
    assert client.calls[0]["model"] == "c/three"


@pytest.mark.parametrize("mutation,message", [
    ("no_count", "needs singers"),
    ("silent_singer", "never sing"),
    ("both_for_three", "two-singer song"),
    ("outside_cast", "from 1 to 3"),
    ("repeated", "each singer once"),
])
def test_invalid_casts_fail_on_load(mutation, message):
    raw = trio_raw()
    if mutation == "no_count":
        del raw["singers"]
    elif mutation == "silent_singer":
        raw["singers"] = 4
    elif mutation == "both_for_three":
        raw["sections"]["hook"]["sung_by"] = "both"
    elif mutation == "outside_cast":
        raw["sections"]["round"]["trade"] = [3, 1, 4]
    else:
        raw["sections"]["hook"]["sung_by"] = [2, 2]
    with pytest.raises(ValueError, match=message):
        spec_from_dict(raw)


def test_solo_song(tmp_path):
    spec = write(tmp_path, solo_raw())
    with pytest.raises(ConfigError, match="for 2 or more singers"):
        Song(RunConfig(["a/one"], spec=spec), ScriptedClient())
    client = ScriptedClient(["<lyrics>We walk back home</lyrics>", "<lyrics>The sky is bright</lyrics>"])
    r = Song(RunConfig(["a/one"], spec=spec, scenario="none"), client).run()
    assert r["scores"]["strict_pass"] and r["config"]["chorus"] == "1"
    system = r["threads"]["1"][0]["content"]
    assert "You are the only singer, one" in system and "other singer" not in system
    assert "isn't only your voice" not in client.calls[0]["messages"][-1]["content"]
    judge = ScriptedClient(['{"singability":8,"humor":7,"parody_craft":7,"coherence":8,"notes":"ok"}'])
    j = rubric(r, judge, "d/judge")
    assert "interplay" not in judge.calls[0]["messages"][0]["content"]
    assert j["scores"]["overall"] == 7.5


def test_lineups_cover_or_balance():
    assert len(lineups(["a", "b", "c"], 2)) == 6
    assert lineups(["a"], 2) == [] and lineups(["a"], 2, include_self=True) == [("a", "a")]
    assert lineups(["a", "b"], 1) == [("a",), ("b",)]
    picked = lineups(["a", "b", "c", "d"], 3, limit=8, seed=1)
    assert len(set(picked)) == 8
    for slot in range(3):
        counts = Counter(lu[slot] for lu in picked)
        assert set(counts.values()) == {2}, counts


def test_matrix_runs_every_lineup_of_a_trio(tmp_path, monkeypatch, capsys):
    spec = write(tmp_path, trio_raw())
    assert main(["matrix", "--models", "a/one,b/two,c/three", "--spec", spec, "--dry-run"]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 6
    assert main(["matrix", "--models", "a/one,b/two", "--spec", spec, "--dry-run"]) == 2
    monkeypatch.setattr("songbench.cli._client", lambda args: ScriptedClient(list(TRIO)))
    out = tmp_path / "runs"
    assert main(["matrix", "--models", "a/one,b/two,c/three", "--spec", spec, "--max-lineups", "2",
                 "--workers", "1", "--out", str(out)]) == 0
    runs = [json.loads(p.read_text()) for p in out.glob("*.json")]
    assert len(runs) == 2 and all(len(r["config"]["models"]) == 3 for r in runs)
    assert len({group_key(r) for r in runs}) == 1
    rows = (out / "matrix.csv").read_text().splitlines()
    assert rows[0].startswith("id,spec,models,scenario") and len(rows) == 3


def test_cli_takes_one_model_per_singer(tmp_path, capsys):
    spec = write(tmp_path, trio_raw())
    args = ["run", "--spec", spec, "--dry-run"]
    assert main(args + ["--model", "a/one", "--model", "b/two"]) == 2
    assert main(args + ["--model", "a/one", "--model", "b/two", "--model", "c/three",
                        "--names", "assigned", "--persona", "X", "--persona", "Y", "--persona", "Z"]) == 0
    out = capsys.readouterr().out
    assert out.count("===== system prompt") == 3
    assert "You are Singer 2, Y" in out
