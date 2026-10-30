"""Synthetic metric regressions; these are not human singability calibration."""
from weird_ai_bench.leaderboard import diagnostics_by_model
from weird_ai_bench.metrics import line_metrics, section_metrics, summarize_metrics
from weird_ai_bench.orchestrate import score_song, rescore
from weird_ai_bench.spec import LineSpec, ProsodySetting, SectionSpec, spec_from_dict
from weird_ai_bench.verify import analyze_line, verify_section
from tests.test_rescore import strict_run


def test_right_count_wrong_stress():
    ls = LineSpec(2, [1])
    m = line_metrics(analyze_line("return", ls), ls)
    assert m["exact_syllables"] and m["syllables"]
    assert not m["stress"]
    assert m["phrase"] is None


def test_melisma_alternatives_and_independent_components():
    ls = LineSpec(prosody=[ProsodySetting("held", [2, 2], [1, 2]),
                           ProsodySetting("attacks", [1, 1, 1, 1], [2, 4])])
    assert line_metrics(analyze_line("Bright light", ls), ls)["exact_syllables"]
    assert not line_metrics(analyze_line("We walk home", ls), ls)["syllables"]
    ls = LineSpec(prosody=[ProsodySetting("pause", [1]*4, [2, 4], [1, 3]),
                           ProsodySetting("stress", [1]*4, [1, 3], [2, 2])])
    report = analyze_line("The sky, is bright", ls)
    m = line_metrics(report, ls)
    assert m["stress"] and m["phrase"]
    # Removing the diagnostic must not change combined scoring gates.
    assert not report.meter_passed(("syllables", "stress", "split"))


def test_slack_is_not_exact_and_missing_stress_fails():
    ls = LineSpec(2, [2], slack=1)
    m = line_metrics(analyze_line("Bright", ls), ls)
    assert m["syllables"] and not m["exact_syllables"]
    assert not m["stress"]


def test_missing_lines_and_rhyme_partner_remain_in_denominators():
    sec = SectionSpec("verse", "Verse", [LineSpec(2, [1], [1, 1], rhyme="A")]*2, {}, singer=1)
    m = summarize_metrics(section_metrics(verify_section(["Bright, light"], sec), sec))
    assert m["expected_lines"] == 2 and m["missing"] == 1
    assert m["syllables"] == {"passed": 1, "total": 2, "rate": .5}
    assert m["stress"]["total"] == m["phrase"]["total"] == 2
    assert m["rhyme"] == {"passed": 0, "total": 2, "rate": 0}
    assert m["copy_checked"] == m["copied"] == 0


def test_copying_is_visible_without_disguising_raw_fit():
    ls = LineSpec(2)
    sec = SectionSpec("verse", "Verse", [ls], {}, singer=1)
    m = summarize_metrics(section_metrics(verify_section(["Bright light"], sec,
                                                        reference=["Bright light"]), sec))
    assert m["syllables"]["rate"] == 1
    assert m["copied"] == m["copy_checked"] == 1


def test_copy_rate_shows_copying_the_fit_rates_let_through():
    ls = LineSpec(2)
    sec = SectionSpec("verse", "Verse", [ls, ls], {}, singer=1)
    rep = verify_section(["Bright light", "Cold night"], sec, reference=["Bright light"])
    run = {"scores": {"by_singer": {"1": {"model": "a/x",
                                          "metrics": summarize_metrics(section_metrics(rep, sec))}}}}
    m = diagnostics_by_model([run])["a/x"]
    assert m["syllables"]["rate"] == 1 and m["copy_rate"] == .5
    legacy = {"scores": {"by_singer": {"1": {"model": "a/x", "adherence": 1}}}}
    assert diagnostics_by_model([run, legacy])["a/x"]["copy_rate"] is None


def test_presets_excluded_and_empty_denominators_unavailable():
    spec = spec_from_dict({"id": "test", "title": "Synthetic", "artist": "Synthetic", "singers": 2,
        "generation_order": ["a", "b"], "performance_order": ["a", "b", "a"],
        "sections": {"a": {"singer": 1, "lines": [{"syllables": 2}]},
                     "b": {"singer": 2, "lines": [{"syllables": 2}]}}})
    out = score_song(spec, 0, ["a/x", "b/y"], {"a": ["Bright light"]},
                     {"a": "fixed", "b": 2}, [], None)
    a, b = (out["scores"]["by_singer"][str(i)]["metrics"] for i in (1, 2))
    assert a["expected_lines"] == 0 and a["syllables"]["rate"] is None
    assert b["expected_lines"] == b["missing"] == 1
    assert b["syllables"]["rate"] == 0 and b["stress"]["rate"] is None


def test_rescore_populates_additive_metrics_without_changing_composite():
    run = strict_run()
    old_scores = {s: b["adherence"] for s, b in run["scores"]["by_singer"].items()}
    for b in run["scores"]["by_singer"].values():
        del b["metrics"]
    updated = rescore(run)
    assert {s: b["adherence"] for s, b in updated["scores"]["by_singer"].items()} == old_scores
    assert all(b["metrics"]["version"] == 1 for b in updated["scores"]["by_singer"].values())
    assert all("metrics" not in b for b in run["scores"]["by_singer"].values())
    assert updated["scoring_version"] == run["scoring_version"] == 5


def test_legacy_or_mixed_run_diagnostics_are_not_fabricated():
    run = strict_run()
    model = run["scores"]["by_singer"]["1"]["model"]
    legacy = {"scores": {"by_singer": {"1": {"model": model, "adherence": 1}}}}
    metrics = diagnostics_by_model([legacy])[model]
    assert metrics["syllables"]["rate"] is None
    metrics = diagnostics_by_model([run, legacy])[model]
    assert metrics["available_singer_runs"] == metrics["missing_singer_runs"] == 1
    assert metrics["syllables"]["rate"] is None
    fresh = diagnostics_by_model([run])[model]
    assert fresh["syllables"]["rate"] is not None


def test_leaderboard_reports_separate_metrics_and_legacy_alias(tmp_path, monkeypatch):
    from tests.test_leaderboard import a_wins, fake_run
    from weird_ai_bench.leaderboard import leaderboard
    a_wins(monkeypatch)
    runs = [fake_run("r0", ["a/x", "a/x"]), fake_run("r1", ["b/y", "b/y"])]
    metrics = summarize_metrics([line_metrics(analyze_line("return", LineSpec(2, [1])), LineSpec(2, [1]))])
    for run in runs:
        for singer in run["scores"]["by_singer"].values():
            singer["metrics"] = metrics
    out = leaderboard(runs, None, "j/judge", tmp_path / "cache.jsonl", bootstrap=0)
    assert out["meter_deprecated_alias"] == "adherence" and out["metrics_version"] == 1
    for row in out["table"]:
        assert row["adherence"] == row["meter"] == 1
        assert row["metrics"]["syllables"]["rate"] == 1
        assert row["metrics"]["stress"]["rate"] == 0
        assert "joint_prosody" not in row["metrics"]
        assert row["metrics"]["expected_lines"] == 2


def test_exact_count_does_not_depend_on_selected_slack_reading(monkeypatch):
    from tests.test_prosody import fake_token
    monkeypatch.setattr("weird_ai_bench.verify.tokenize",
                        lambda *_: [fake_token([(0, 1), (1, 0, 0)])])
    ls = LineSpec(2, [1], slack=[0, 1])
    report = analyze_line("example", ls)
    assert report.count == 3  # chosen for its stress, not exact count
    assert line_metrics(report, ls)["exact_syllables"]


def test_null_legacy_metrics_are_unavailable():
    run = {"scores": {"by_singer": {"1": {"model": "a/x", "metrics": None}}}}
    assert diagnostics_by_model([run])["a/x"]["syllables"]["rate"] is None


def test_metrics_do_not_emit_joint_prosody():
    ls = LineSpec(2, [1])
    metrics = line_metrics(analyze_line("Bright light", ls), ls)
    assert "joint_prosody" not in metrics
    assert "joint_prosody" not in summarize_metrics([metrics])


def test_leaderboard_cli_has_no_joint_column(tmp_path, monkeypatch, capsys):
    import json
    from weird_ai_bench.cli import main
    from tests.test_leaderboard import a_wins, fake_run
    a_wins(monkeypatch)
    monkeypatch.setattr("weird_ai_bench.cli.OpenRouterClient", lambda **kwargs: None)
    for i, model in enumerate(("a/x", "b/y")):
        (tmp_path / f"run{i}.json").write_text(json.dumps(fake_run(f"r{i}", [model, model])))
    assert main(["leaderboard", str(tmp_path), "--judge", "j/judge", "--bootstrap", "0"]) == 0
    output = capsys.readouterr().out
    assert "adher" in output and "syll" in output
    assert "joint" not in output
