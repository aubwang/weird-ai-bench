"""Exact, authored text-to-note settings; synthetic lyrics only."""

from dataclasses import asdict

import pytest

from weird_ai_bench.cli import main
from weird_ai_bench.judge import _context, check_notes
from weird_ai_bench.llm import ScriptedClient
from weird_ai_bench.orchestrate import ConfigError, RunConfig, Song, rescore
from weird_ai_bench.phonetics import Pron, Token, WordInfo
from weird_ai_bench.spec import (LineSpec, ProsodySetting, SectionSpec, describe_line,
                                 load_spec, spec_from_dict)
from weird_ai_bench.verify import analyze_line, verify_section


def melisma_line():
    return LineSpec(prosody=[
        ProsodySetting("four-attacks", [1, 1, 1, 1], [2, 4]),
        ProsodySetting("two-held-syllables", [2, 2], [1, 2]),
    ])


def solo_spec(line=None):
    return spec_from_dict({
        "id": "held_notes", "title": "Held Notes", "artist": "Synthetic",
        "singers": 1, "generation_order": ["verse"], "performance_order": ["verse"],
        "sections": {"verse": {"singer": 1, "lines": [asdict(line or melisma_line())]}},
    })


def test_melisma_has_exact_alternatives_not_a_count_interval():
    line = melisma_line()
    four = analyze_line("The sky is bright", line)
    two = analyze_line("Bright light", line)
    assert four.syllables_ok and four.stress_ok and four.setting_name == "four-attacks"
    assert two.syllables_ok and two.stress_ok and two.setting_name == "two-held-syllables"
    assert two.count == 2 and sum(two.note_spans) == 4
    assert two.allowed_counts == [2, 4]
    assert not analyze_line("We walk home", line).syllables_ok  # 3 is not an allowed alternative
    assert not analyze_line("We walk back home now", line).syllables_ok
    assert not analyze_line("", line).syllables_ok
    assert (two.under, two.over) == (0, 0)
    with pytest.raises(ValueError, match="cannot use --tolerance"):
        analyze_line("We walk home", line, tolerance=1)


def test_setting_specific_stress_and_phrase_boundaries():
    line = LineSpec(prosody=[
        ProsodySetting("first-accent", [2, 1], [1]),
        ProsodySetting("last-accent", [1, 2], [2]),
    ])
    rep = analyze_line("return", line)
    assert rep.syllables_ok and rep.stress_ok and rep.setting_name == "last-accent"
    line = LineSpec(prosody=[ProsodySetting("held-ending", [1, 1, 2], [2, 3], [2, 1])])
    good = analyze_line("The sky, shines", line)
    assert good.syllables_ok and good.stress_ok and good.split_ok
    assert analyze_line("The sky shines", line).split_ok is False


def test_constraints_cannot_be_borrowed_across_settings():
    line = LineSpec(prosody=[
        ProsodySetting("wrong-pause", [1, 1, 1, 1], [2, 4], [1, 3]),
        ProsodySetting("wrong-stress", [1, 1, 1, 1], [1, 3], [2, 2]),
    ])
    sec = SectionSpec("verse", "Verse", [line], {}, singer=1)
    rep = verify_section(["The sky, is bright"], sec)
    assert not rep.passed()
    assert "no single declared prosody setting" in " ".join(rep.errors())


def fake_token(stresses, break_after=False):
    return Token(WordInfo("example", "example", [Pron(("X",), s) for s in stresses],
                          weak=False, guessed=False), break_after)


def test_one_pronunciation_must_supply_all_stresses(monkeypatch):
    monkeypatch.setattr("weird_ai_bench.verify.tokenize", lambda *_: [fake_token([(1, 0), (0, 1)])])
    rep = analyze_line("example", LineSpec(2, [1, 2]))
    assert rep.syllables_ok and rep.stress_hits == 1 and not rep.stress_ok


def test_joint_constraints_beat_nearest_legacy_count(monkeypatch):
    monkeypatch.setattr("weird_ai_bench.verify.tokenize", lambda *_: [fake_token([(0, 1), (1, 0, 0)])])
    rep = analyze_line("example", LineSpec(2, [1], slack=[0, 1]))
    assert rep.count == 3 and rep.syllables_ok and rep.stress_ok


def test_joint_split_and_stress_use_the_same_pronunciation(monkeypatch):
    tokens = [fake_token([(1,), (1, 0)], True), fake_token([(1,), (0, 1)])]
    monkeypatch.setattr("weird_ai_bench.verify.tokenize", lambda *_: tokens)
    # Pause at 2 forces the first word's long reading; its syllable 2 is weak.
    rep = analyze_line("example, example", LineSpec(3, [2], [2, 1]))
    assert rep.syllables_ok and not (rep.stress_ok and rep.split_ok)


@pytest.mark.parametrize("kwargs", [{"slack": 1}, {"tolerance": 1}])
def test_a_missing_stressed_syllable_never_earns_credit(kwargs):
    tolerance = kwargs.get("tolerance", 0)
    line = LineSpec(2, [2], slack=kwargs.get("slack", 0))
    rep = analyze_line("Bright", line, tolerance=tolerance)
    assert rep.syllables_ok and rep.stress_required == 1 and rep.stress_hits == 0
    assert not rep.stress_ok and "syllable 2 is missing" in rep.stress_issues


def test_legacy_snapshot_still_loads_without_new_fields():
    raw = asdict(load_spec("two_voices"))
    for section in raw["sections"].values():
        for line in section["lines"]:
            line.pop("prosody")
    spec = spec_from_dict(raw)
    assert analyze_line("The sky is bright", spec.sections["opening"].lines[0]).syllables_ok
    assert not any(l.prosody for s in spec.sections.values() for l in s.lines)


@pytest.mark.parametrize("setting", [
    {}, {"name": "x"}, {"name": "x", "note_spans": []},
    {"name": "", "note_spans": [1]}, {"name": "x", "note_spans": [0]},
    {"name": "x", "note_spans": [True]}, {"name": "x", "note_spans": [1.5]},
    {"name": "x", "note_spans": "1"}, {"name": "x", "note_spans": [1], "stress": [2]},
    {"name": "x", "note_spans": [1], "stress": [True]},
    {"name": "x", "note_spans": [1], "stress": [1, 1]},
    {"name": "x", "note_spans": [1, 1], "split": [1, 0, 1]},
    {"name": "x", "note_spans": [1, 1], "typo": 1},
])
def test_invalid_prosody_is_rejected(setting):
    raw = asdict(solo_spec())
    raw["sections"]["verse"]["lines"][0]["prosody"] = [setting]
    with pytest.raises(ValueError):
        spec_from_dict(raw)


@pytest.mark.parametrize("mutation", ["notes", "names", "syllables", "stress", "split", "slack", "empty"])
def test_ambiguous_or_inconsistent_line_settings_are_rejected(mutation):
    raw = asdict(solo_spec())
    line = raw["sections"]["verse"]["lines"][0]
    if mutation == "notes":
        line["prosody"][1]["note_spans"] = [2, 3]
    elif mutation == "names":
        line["prosody"][1]["name"] = line["prosody"][0]["name"]
    elif mutation == "empty":
        line["prosody"] = []
    else:
        line[mutation] = {"syllables": 4, "stress": [2], "split": [2, 2], "slack": 1}[mutation]
    with pytest.raises(ValueError):
        spec_from_dict(raw)


@pytest.mark.parametrize("count", [0, -1, True, 1.5, "4"])
def test_invalid_legacy_counts_are_rejected(count):
    with pytest.raises(ValueError, match="syllables"):
        LineSpec(count)


def test_explicit_setting_round_trip_retry_and_judge_context(tmp_path, capsys):
    spec = solo_spec()
    assert spec_from_dict(asdict(spec)) == spec
    client = ScriptedClient(["<lyrics>We walk home</lyrics>", "<lyrics>Bright light</lyrics>"])
    result = Song(RunConfig(["a/one"], scenario="none"), client, spec=spec).run()
    assert result["scores"]["strict_pass"] and result["turns"][0]["retries"] == 1
    assert "it needs 2 or 4" in client.calls[1]["messages"][-1]["content"]
    assert "one complete declared prosody setting" in client.calls[0]["messages"][-1]["content"]
    assert "melisma" in client.calls[0]["messages"][0]["content"]
    assert rescore(result)["verification"] == result["verification"]
    assert "two-held-syllables" in check_notes(result)
    assert "not observations of a performance" in _context(result)
    assert "notes per syllable [2, 2]" in _context(result)
    assert "OR" in describe_line(spec.sections["verse"].lines[0], 1, {})

    import yaml
    path = tmp_path / "held.yaml"
    path.write_text(yaml.safe_dump(asdict(spec)))
    text = tmp_path / "held.txt"
    text.write_text("[verse]\nBright light\n")
    assert main(["check", str(text), "--spec", str(path)]) == 0
    assert "setting: two-held-syllables" in capsys.readouterr().out


def test_tolerance_conflict_is_rejected_before_any_generation():
    client = ScriptedClient()
    with pytest.raises(ConfigError, match="tolerance"):
        Song(RunConfig(["a/one"], scenario="none", tolerance=1), client, spec=solo_spec())
    assert not client.calls


def test_judge_sees_stress_phrase_and_pronunciation_uncertainty():
    spec = solo_spec(LineSpec(4, [2, 4], [2, 2]))
    result = Song(RunConfig(["a/one"], scenario="none", track="freeform"),
                  ScriptedClient(["<lyrics>The cat and the</lyrics>"]), spec=spec).run()
    notes = check_notes(result)
    assert "unstressed" in notes or "weak word" in notes
    assert "required phrase boundary" in notes
    result["verification"]["verse"]["lines"][0]["guessed_words"] = ["inventedword"]
    assert "estimated pronunciations: inventedword" in check_notes(result)


def test_disabled_gate_cannot_trigger_retry_through_setting_selection():
    line = LineSpec(prosody=[
        ProsodySetting("stress-first", [1, 1, 1, 1], [2, 4], [1, 3]),
        ProsodySetting("split-first", [1, 1, 1, 1], [1, 3], [2, 2]),
    ])
    rep = verify_section(["The sky, is bright"], SectionSpec("v", "V", [line], {}, singer=1))
    assert not rep.passed()
    assert rep.passed(["syllables", "split"])
    assert rep.errors(["syllables", "split"]) == []
    assert rep.passed(["syllables", "stress"])
    assert rep.errors(["syllables", "stress"]) == []
    assert rep.gate("stress") and rep.gate("split")
    assert not rep.to_dict()["meter_joint_pass"]


def test_disabled_gate_cannot_trigger_retry_through_pronunciation_selection(monkeypatch):
    tokens = [fake_token([(1,), (0, 0)], True), fake_token([(1, 1, 1), (1, 1)])]
    monkeypatch.setattr("weird_ai_bench.verify.tokenize", lambda *_: tokens)
    line = LineSpec(4, [1, 2], [2, 2])
    rep = verify_section(["example, example"], SectionSpec("v", "V", [line], {}, singer=1))
    assert not rep.passed()
    assert rep.passed(["syllables", "split"])
    assert rep.errors(["syllables", "split"]) == []
    assert rep.passed(["syllables", "stress"])


def test_freeform_numeric_scores_do_not_depend_on_retry_gates():
    line = LineSpec(prosody=[
        ProsodySetting("stress-first", [1, 1, 1, 1], [2, 4], [1, 3]),
        ProsodySetting("split-first", [1, 1, 1, 1], [1, 3], [2, 2]),
    ])
    runs = [Song(RunConfig(["a/one"], scenario="none", gates=gates),
                 ScriptedClient(["<lyrics>The sky, is bright</lyrics>"]),
                 spec=solo_spec(line)).run()
            for gates in (["syllables", "stress"], ["syllables", "split"])]
    assert all(r["scores"]["strict_pass"] for r in runs)
    assert runs[0]["verification"] == runs[1]["verification"]
    assert runs[0]["scores"]["adherence"] == runs[1]["scores"]["adherence"]


def test_synthetic_melisma_example_and_tolerance_cli(capsys):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    args = ["check", str(root / "examples/melisma.txt"),
            "--spec", str(root / "examples/melisma.yaml")]
    assert main(args) == 0
    assert "setting: held-ending" in capsys.readouterr().out
    assert main([*args, "--tolerance", "1"]) == 2
    assert "cannot use --tolerance" in capsys.readouterr().err
    assert main([*args, "--tolerance", "-1"]) == 2
    assert "whole number 0 or more" in capsys.readouterr().err
