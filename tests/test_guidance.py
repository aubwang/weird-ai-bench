"""Unguided runs: prompts carry the reference lyrics and line counts, never the song map."""

from dataclasses import asdict

import pytest
import yaml

from songbench.cli import main
from songbench.leaderboard import gate_stats, group_key
from songbench.llm import ScriptedClient
from songbench.orchestrate import ConfigError, RunConfig, Song
from songbench.spec import load_spec

SCRIPT = ["<lyrics>We watch the light\nWe walk back home</lyrics>",
          "<lyrics>The sky is bright</lyrics>",
          "<lyrics>You take the road</lyrics>", "<lyrics>I take the train</lyrics>",
          "<lyrics>Now we walk back home</lyrics>"]
# Words that only appear when a prompt describes the song map.
MAP_WORDS = ("syllable", "stress", "rhyme", "hook", "invitation")


def run(guidance, track="freeform"):
    client = ScriptedClient(list(SCRIPT))
    result = Song(RunConfig(["a/one", "b/two"], track=track, guidance=guidance), client).run()
    return result, client


def prompt_text(client):
    return "\n".join(m["content"] for c in client.calls for m in c["messages"]
                     if m["role"] in ("system", "user"))


def test_unguided_prompts_leave_out_the_song_map():
    _, client = run("none")
    text = prompt_text(client).lower()
    for word in MAP_WORDS:
        assert word not in text, word
    assert "<reference_lyrics>" in text and "you take the road" in text
    assert "write all 2 lines." in text
    assert "order: line 1 by singer 1, line 2 by singer 2." in text


def test_guided_prompts_still_carry_the_song_map():
    _, client = run("full")
    text = prompt_text(client).lower()
    assert "syllable" in text and "stress" in text and "invitation" in text


def test_unguided_runs_are_still_scored():
    result, _ = run("none")
    assert result["config"]["guidance"] == "none"
    assert result["scores"]["by_singer"]["1"]["adherence"] == 1
    assert "-unguided-" in result["id"]
    assert all(t["retries"] == 0 for t in result["turns"])


def test_unguided_needs_freeform():
    with pytest.raises(ConfigError, match="freeform"):
        run("none", track="strict")


def test_unguided_needs_reference_lyrics(tmp_path):
    spec = load_spec("two_voices")
    for sec in spec.sections.values():
        for line in sec.lines:
            line.reference = None
    path = tmp_path / "bare.yaml"
    path.write_text(yaml.safe_dump(asdict(spec)))
    with pytest.raises(ConfigError, match="reference lyrics"):
        Song(RunConfig(["a/one", "b/two"], track="freeform", guidance="none", spec=str(path)),
             ScriptedClient([]))


def test_guidance_separates_groups_and_stats():
    full, _ = run("full")
    none, _ = run("none")
    assert group_key(full) != group_key(none)
    old = dict(full, config={k: v for k, v in full["config"].items() if k != "guidance"})
    assert group_key(old) == group_key(full)
    rows = gate_stats([full, none])
    assert {(r["model"], r["guidance"]) for r in rows} == {
        ("a/one", "full"), ("b/two", "full"), ("a/one", "none"), ("b/two", "none")}


def test_dry_run_shows_unguided_prompts(capsys):
    assert main(["run", "--model", "a/one", "--model", "b/two", "--track", "freeform",
                 "--guidance", "none", "--dry-run"]) == 0
    out = capsys.readouterr().out.lower()
    assert "syllable" not in out and "write the refrain" in out
