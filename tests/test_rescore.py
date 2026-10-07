"""Rescoring saved runs, scoring versions, and checks the source lyrics must pass."""

import json
from dataclasses import asdict

import pytest

from weird_ai_bench.cli import main
from weird_ai_bench.llm import ScriptedClient
from weird_ai_bench.orchestrate import ConfigError, RunConfig, Song, rescore, save
from weird_ai_bench.spec import LineSpec, ProsodySetting, load_spec
from weird_ai_bench.verify import GATES, SCORING_VERSION, verify_section

CHORUS = "<lyrics>We chase the dawn\nWe head for town</lyrics>"
BAD = "<lyrics>A moon stays very high</lyrics>"
OPENING = "<lyrics>A moon stays high</lyrics>"
TAIL = ["<lyrics>Take me along</lyrics>", "<lyrics>I'll meet you there</lyrics>",
        "<lyrics>Now we head for town</lyrics>"]


def strict_run():
    return Song(RunConfig(["a/one", "b/two"]), ScriptedClient([CHORUS, BAD, OPENING, *TAIL])).run()


def test_rescore_matches_a_fresh_run():
    r = strict_run()
    again = rescore(r)
    for key in ("parts", "verification", "scores", "turns", "originality", "scoring_version",
                "generation_scoring_version"):
        assert again[key] == r[key], key
    assert r["scoring_version"] == SCORING_VERSION
    assert r["generation_scoring_version"] == SCORING_VERSION


@pytest.mark.parametrize("old_version", [None, 2, 3])
def test_rescore_preserves_original_generation_version(old_version):
    r = strict_run()
    del r["generation_scoring_version"]
    if old_version is None:
        del r["scoring_version"]
    else:
        r["scoring_version"] = old_version
    original = json.dumps(r, sort_keys=True)
    updated = rescore(r)
    assert updated["generation_scoring_version"] == (old_version or 1)
    assert updated["scoring_version"] == SCORING_VERSION
    assert rescore(updated)["generation_scoring_version"] == (old_version or 1)
    assert [t["retries"] for t in updated["turns"]] == [t["retries"] for t in r["turns"]]
    assert json.dumps(r, sort_keys=True) == original


def test_failed_run_records_generation_version():
    song = Song(RunConfig(["a/one", "b/two"]), ScriptedClient([]))
    result = song.failed_result("synthetic failure")
    assert result["generation_scoring_version"] == SCORING_VERSION
    assert rescore(result)["generation_scoring_version"] == SCORING_VERSION


@pytest.mark.parametrize("tolerance", [-1, True, 0.5, "1"])
def test_invalid_tolerance_is_rejected_before_generation(tolerance):
    with pytest.raises(ConfigError, match="tolerance must be a whole number"):
        Song(RunConfig(["a/one", "b/two"], tolerance=tolerance), ScriptedClient([]))


def test_exact_prosody_rejects_tolerance_before_generation():
    spec = load_spec("two_voices")
    spec.sections["opening"].lines[0] = LineSpec(prosody=[
        ProsodySetting(name="one syllable per note", note_spans=[1, 1, 1, 1])])
    with pytest.raises(ConfigError, match="Exact prosody settings cannot use --tolerance"):
        Song(RunConfig(["a/one", "b/two"], tolerance=1), ScriptedClient([]), spec=spec)
    RunConfig(["a/one", "b/two"], tolerance=0).validate(spec)
    RunConfig(["a/one", "b/two"], tolerance=1).validate(load_spec("two_voices"))


def test_rescore_reparses_raw_responses():
    r = strict_run()
    r["parts"]["ending"]["lines"] = ["Now we head for town", "</lyrics>"]
    r["turns"][-1]["attempts"][-1]["response"] = "Now we head for town\n</lyrics>"
    assert rescore(r)["parts"]["ending"]["lines"] == ["Now we head for town"]


def test_rescore_against_a_revised_template(tmp_path):
    r = Song(RunConfig(["a/one", "b/two"], track="freeform"),
             ScriptedClient([CHORUS, BAD, *TAIL])).run()
    assert not r["turns"][1]["first_try_pass"]
    spec = load_spec("two_voices")
    spec.sections["opening"].lines[0].slack = [0, 2]
    new = rescore(r, spec)
    assert new["turns"][1]["first_try_pass"] and new["scores"]["strict_pass"]
    assert new["spec_snapshot"] == asdict(spec)
    assert new["turns"][1]["retries"] == 0
    spec.sections["opening"].lines.append(spec.sections["opening"].lines[0])
    with pytest.raises(ValueError, match="same sections"):
        rescore(r, spec)


def test_stats_refuses_mixed_versions_until_rescored(tmp_path, capsys):
    old, new = strict_run(), strict_run()
    del old["scoring_version"]
    save(old, tmp_path)
    save(dict(new, id=new["id"] + "-b"), tmp_path)
    assert main(["stats", str(tmp_path)]) == 2
    assert "different rules" in capsys.readouterr().err
    assert main(["rescore", str(tmp_path)]) == 0
    assert all(json.loads(p.read_text())["scoring_version"] == SCORING_VERSION
               for p in tmp_path.glob("*.json"))
    assert main(["stats", str(tmp_path)]) == 0


def test_reference_lyrics_pass_every_check():
    """The source song must pass its own template, or the rules are wrong."""
    spec = load_spec("two_voices")
    hook = next(l.reference for s in spec.sections.values() for l in s.lines if l.hook)
    for sec in spec.sections.values():
        rep = verify_section([l.reference for l in sec.lines], sec, spec.syllable_overrides, hook=hook)
        assert rep.passed(GATES), (sec.key, rep.errors())
        assert rep.scores()["overall"] == 1, (sec.key, rep.scores())
