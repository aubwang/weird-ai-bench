"""End-to-end runs and regression checks using the synthetic template."""

import json
import math
from dataclasses import asdict

import pytest
import yaml

from songbench.cli import main
from songbench.judge import pairwise, rubric
from songbench.leaderboard import fit_additive_bt, gate_stats, group_key
from songbench.llm import LLMError, ScriptedClient
from songbench.orchestrate import ConfigError, Duet, RunConfig, render_sheet, save
from songbench.prompts import parse_lyrics
from songbench.spec import load_spec, result_spec


CHORUS = "<lyrics>We watch the light\nWe walk back home</lyrics>"
OPENING = "<lyrics>The sky is bright</lyrics>"
BAD = "<lyrics>The sky is very bright</lyrics>"
TAIL = ["<lyrics>You take the road</lyrics>", "<lyrics>I take the train</lyrics>",
        "<lyrics>Now we walk back home</lyrics>"]


def script():
    return [CHORUS, OPENING, *TAIL]


def test_strict_retries_and_hides_failed_draft(tmp_path):
    client = ScriptedClient([CHORUS, BAD, OPENING, *TAIL])
    r = Duet(RunConfig("a/one", "b/two"), client).run()
    turn = next(t for t in r["turns"] if t["section"] == "opening")
    assert turn["retries"] == 1 and not turn["first_try_pass"] and turn["final_pass"]
    assert "very bright" not in " ".join(m["content"] for m in r["threads"]["2"])
    assert r["scores"]["strict_pass"]
    jp, mp = save(r, tmp_path)
    assert json.loads(jp.read_text())["id"] == r["id"]
    assert "Opening" in mp.read_text()


def test_freeform_does_not_retry():
    r = Duet(RunConfig("a/one", "b/two", track="freeform"),
             ScriptedClient([CHORUS, BAD, *TAIL])).run()
    assert not r["scores"]["strict_pass"]
    assert all(t["retries"] == 0 for t in r["turns"])
    assert r["scores"]["by_singer"]["1"]["adherence"] < 1
    assert r["scores"]["by_singer"]["2"]["adherence"] == 1


def test_strict_exhausts_retries_and_continues():
    r = Duet(RunConfig("a/one", "b/two", max_retries=2),
             ScriptedClient([CHORUS, BAD, BAD, BAD, *TAIL])).run()
    assert r["turns"][1]["retries"] == 2
    assert not r["turns"][1]["final_pass"]
    assert r["parts"]["ending"]["lines"] == ["Now we walk back home"]


def test_chorus_can_be_written_by_second_singer():
    client = ScriptedClient(script())
    r = Duet(RunConfig("a/one", "b/two", chorus="model_2"), client).run()
    assert client.calls[0]["model"] == "b/two"
    assert r["parts"]["refrain"]["author"] == 2
    assert r["scores"]["strict_pass"]


def test_anonymous_and_assigned_names():
    with pytest.raises(ConfigError):
        Duet(RunConfig("a/one", "b/two", names="anonymous"), ScriptedClient())
    with pytest.raises(ConfigError):
        Duet(RunConfig("a/one", "b/two", names="assigned"), ScriptedClient())
    d = Duet(RunConfig("a/one", "b/two", names="assigned", persona_1="North", persona_2="South"), ScriptedClient())
    assert "You are Singer 1, North" in d.threads[1][0]["content"]
    d = Duet(RunConfig("a/one", "b/two", names="anonymous", mode="third_party"), ScriptedClient())
    assert "a/one" not in d.threads[1][0]["content"]


def test_parse_annotations_and_keep_adlibs():
    text = "<lyrics>\n1. The sky is bright [4]\n**We head home** (3)\nWe walk home <adlib>home</adlib>\n</lyrics>"
    assert parse_lyrics(text) == ["The sky is bright", "We head home", "We walk home <adlib>home</adlib>"]


def test_blind_judging_and_stats():
    r = Duet(RunConfig("a/one", "b/two"), ScriptedClient(script())).run()
    assert "a/one" not in render_sheet(r, blind=True)
    jc = ScriptedClient(['{"singability":8,"humor":9,"parody_craft":7,"coherence":8,"interplay":9,"notes":"ok"}'])
    j = rubric(r, jc, "a/judge")
    assert j["scores"]["humor"] == 9 and "warning" in j
    for votes, winner in [(['{"winner":1}', '{"winner":2}'], "a"),
                          (['{"winner":1}', '{"winner":1}'], "tie")]:
        assert pairwise(r, dict(r, id="other"), ScriptedClient(votes), "c/judge")["winner"] == winner
    assert all(row["first_try_pass"] == 1 for row in gate_stats([r]))


@pytest.mark.parametrize("n", [10, 100, 200, 1000])
def test_bt_recovers_majority_at_different_sample_sizes(n):
    comps = [(["a", "c"], ["b", "c"], 1.0)] * (n * 6 // 10)
    comps += [(["a", "c"], ["b", "c"], 0.0)] * (n * 4 // 10)
    strengths = fit_additive_bt(comps)
    probability = 1 / (1 + math.exp(-(strengths["a"] - strengths["b"])))
    assert probability == pytest.approx(0.6, abs=0.001)
    assert strengths["c"] == pytest.approx(0)


@pytest.mark.parametrize("spec_id", ["custom_song", "two_voices"])
def test_custom_spec_survives_source_removal(tmp_path, spec_id):
    spec = load_spec()
    spec.id = spec_id
    spec.title = "Custom template"
    spec.sections["opening"].label = "Custom opening"
    path = tmp_path / "custom.yaml"
    path.write_text(yaml.safe_dump(asdict(spec)))
    r = Duet(RunConfig("a/one", "b/two", spec=str(path)), ScriptedClient(script())).run()
    jp, mp = save(r, tmp_path / "runs")
    path.unlink()
    loaded = json.loads(jp.read_text())
    assert asdict(result_spec(loaded)) == asdict(spec)
    assert "Custom opening" in render_sheet(loaded)
    assert "Custom template" in mp.read_text()
    judge = ScriptedClient(['{"singability":8,"notes":"ok"}'])
    rubric(loaded, judge, "c/judge")
    assert "Custom template" in judge.calls[0]["messages"][0]["content"]


def test_legacy_run_and_template_grouping():
    from copy import deepcopy
    r = Duet(RunConfig("a/one", "b/two"), ScriptedClient(script())).run()
    other = deepcopy(r)
    other["spec_snapshot"]["sections"]["opening"]["lines"][0]["syllables"] += 1
    assert group_key(r) != group_key(other)
    key = group_key(r)
    del r["spec_snapshot"]
    assert "Opening" in render_sheet(r)
    assert group_key(r) == key


@pytest.mark.parametrize("track", ["freeform", "strict"])
def test_empty_chorus_does_not_crash(track, tmp_path):
    r = Duet(RunConfig("a/one", "b/two", track=track, max_retries=1), ScriptedClient()).run()
    assert r["parts"]["refrain"]["lines"] == []
    assert not r["scores"]["strict_pass"]
    assert r["verification"]["refrain"]["structure_errors"]
    save(r, tmp_path)


@pytest.mark.parametrize("command", ["run", "matrix"])
@pytest.mark.parametrize("failure", ["api", "json"])
def test_judge_failure_keeps_song(monkeypatch, tmp_path, command, failure):
    monkeypatch.setattr("songbench.cli._client", lambda args: ScriptedClient(script()))
    def fail_judge(*args):
        if failure == "api":
            raise LLMError("simulated judge outage")
        raise ValueError("invalid judge JSON")
    monkeypatch.setattr("songbench.judge.rubric", fail_judge)
    args = [command, "--judge", "c/judge", "--out", str(tmp_path)]
    args += (["--model-1", "a/one", "--model-2", "b/two"] if command == "run"
             else ["--models", "a/one", "--include-self", "--workers", "1"])
    if command == "run" and failure == "json":
        with pytest.raises(ValueError):
            main(args)
    else:
        assert main(args) == 1
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    r = json.loads(files[0].read_text())
    assert r["scores"]["strict_pass"] and "judge" not in r
    assert files[0].with_suffix(".md").exists()
