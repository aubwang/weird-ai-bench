"""Leaderboard: the Bradley-Terry fit, credit weights, pair selection, forfeits, and stats."""

import json
import math
import random
from dataclasses import asdict

import pytest

from songbench import leaderboard as lb
from songbench.judge import JUDGE_VERSION
from songbench.leaderboard import fit_additive_bt, gate_stats, group_key, leaderboard, singer_weights
from songbench.llm import ScriptedClient
from songbench.orchestrate import RunConfig, Song
from songbench.spec import load_spec

SPEC = asdict(load_spec("two_voices"))
SCENARIO = {"id": "s", "text": "a setup", "per_singer": {}}


def fake_run(rid, models, chorus=1, failed=None, **cfg):
    """A minimal two_voices run: `chorus` is the singer who wrote the chorus, or 'fixed'."""
    c = {"models": models, "names": "real", "chorus": str(chorus), "track": "strict",
         "guidance": "full", "spec": "two_voices", "personas": [None] * len(models), **cfg}
    parts = {"refrain": {"lines": ["We watch the light", "We walk back home"], "author": chorus},
             "opening": {"lines": ["The sky is bright"], "author": 1},
             "exchange": {"lines": ["You take the road", "I take the train"], "author": [1, 2]},
             "ending": {"lines": ["Now we walk back home"], "author": 2}}
    by_singer = {str(i + 1): {"model": m, "adherence": 1.0} for i, m in enumerate(models)}
    turns = [{"singer": i + 1, "first_try_pass": True, "final_pass": True, "retries": 0}
             for i in range(len(models))]
    run = {"version": 2, "id": rid, "spec": "two_voices", "spec_snapshot": SPEC,
           "scenario_snapshot": SCENARIO, "config": c, "parts": parts, "turns": turns,
           "reference_lyrics": None, "scores": {"by_singer": by_singer}}
    if failed:
        run["failed"] = {"error": failed, "section": "ending"}
    return run


def a_wins(monkeypatch):
    def fake(a, b, client, judge):
        return {"a": a["id"], "b": b["id"], "winner": "a", "score_a": 1.0, "votes": ["a", "a"],
                "judge": judge, "judge_version": JUDGE_VERSION}

    monkeypatch.setattr(lb, "pairwise", fake)


class Judge:
    """Always prefers the first song in whichever order it is shown."""

    def __init__(self, winner=1):
        self.calls = 0
        self.winner = winner

    def complete(self, model, messages, **kw):
        self.calls += 1
        return type("C", (), {"text": json.dumps({"winner": self.winner}), "cost": 0.0})()


def grad(comps, theta, prior_sd=1.0):
    g = {m: -v / prior_sd ** 2 for m, v in theta.items()}
    for wa, wb, y in comps:
        d = sum(w * theta[m] for m, w in wa.items()) - sum(w * theta[m] for m, w in wb.items())
        p = 1 / (1 + math.exp(-d))
        for m, w in wa.items():
            g[m] += (y - p) * w
        for m, w in wb.items():
            g[m] -= (y - p) * w
    return g


def simulate(true, n, seed=1):
    rng = random.Random(seed)
    models = sorted(true)
    comps = []
    for _ in range(n):
        a, b = rng.sample(models, 2)
        p = 1 / (1 + math.exp(-(true[a] - true[b])))
        comps.append(({a: 1.0}, {b: 1.0}, 1.0 if rng.random() < p else 0.0))
    return comps


def test_newton_recovers_strengths_and_is_stationary():
    true = {"a": 1.0, "b": 0.0, "c": -1.0}
    comps = simulate(true, 6000)
    fit = fit_additive_bt(comps, prior_sd=10.0)
    assert sum(fit.values()) == pytest.approx(0, abs=1e-9)
    for m in true:
        assert fit[m] == pytest.approx(true[m], abs=0.15)
    g = grad(comps, fit, prior_sd=10.0)
    assert max(abs(v) for v in g.values()) < 1e-6


def test_fit_is_a_fixed_point_not_an_iteration_artifact():
    comps = simulate({"a": 0.5, "b": -0.5, "c": 0.0}, 50, seed=4)
    fit = fit_additive_bt(comps)
    assert max(abs(v) for v in grad(comps, fit).values()) < 1e-7
    assert fit_additive_bt(comps) == fit


def test_perfect_separation_is_finite_and_bounded_by_prior():
    comps = [({"a": 1.0}, {"b": 1.0}, 1.0)] * 20
    gap = fit_additive_bt(comps)
    assert math.isfinite(gap["a"]) and 0 < gap["a"] - gap["b"] < 6
    wide = fit_additive_bt(comps, prior_sd=3.0)
    assert wide["a"] - wide["b"] > gap["a"] - gap["b"]
    assert fit_additive_bt([]) == {}


def test_comparison_weights_count_like_repeats():
    comps = [({"a": 1.0}, {"b": 1.0}, 1.0), ({"a": 1.0}, {"b": 1.0}, 0.0),
             ({"a": 1.0}, {"c": 1.0}, 1.0)]
    repeated = fit_additive_bt(comps + comps[:1] * 2)
    weighted = fit_additive_bt(comps, weights=[3, 1, 1])
    for m in "abc":
        assert weighted[m] == pytest.approx(repeated[m], abs=1e-9)


def test_weights_follow_shares_not_slots():
    comps = [({"a": 0.75, "b": 0.25}, {"b": 1.0}, 1.0)] * 10
    fit = fit_additive_bt(comps)
    assert fit["a"] > fit["b"]
    # a's share is 0.75, so a fully separated win moves the gap by less than a solo win would.
    solo = fit_additive_bt([({"a": 1.0}, {"b": 1.0}, 1.0)] * 10)
    assert fit["a"] - fit["b"] > 0 and solo["a"] - solo["b"] > 0


def test_self_duet_weight_is_one():
    assert singer_weights(fake_run("r", ["a/x", "a/x"])) == {"a/x": 1.0}


def test_two_voices_weights_reflect_chorus_author_and_repeats():
    # Performance: opening(1), refrain x2 (2 lines each), exchange (1 each), ending(2).
    by1 = singer_weights(fake_run("r", ["a/x", "b/y"], chorus=1))
    assert by1 == {"a/x": 6 / 8, "b/y": 2 / 8}
    by2 = singer_weights(fake_run("r", ["a/x", "b/y"], chorus=2))
    assert by2 == {"a/x": 2 / 8, "b/y": 6 / 8}
    given = singer_weights(fake_run("r", ["a/x", "b/y"], chorus="fixed"))
    assert given == {"a/x": 0.5, "b/y": 0.5}


def test_weights_from_a_real_run():
    client = ScriptedClient(["<lyrics>We watch the light\nWe walk back home</lyrics>",
                             "<lyrics>The sky is bright</lyrics>", "<lyrics>You take the road</lyrics>",
                             "<lyrics>I take the train</lyrics>", "<lyrics>Now we walk back home</lyrics>"])
    run = Song(RunConfig(["a/x", "b/y"]), client).run()
    assert singer_weights(run) == {"a/x": 0.75, "b/y": 0.25}


def test_failed_run_weights_use_the_template_assignment():
    run = fake_run("r", ["a/x", "b/y"], chorus=1, failed="boom")
    run["parts"]["ending"] = {"lines": [], "author": None}
    run["parts"]["exchange"] = {"lines": [], "author": None}
    run["parts"]["refrain"] = {"lines": [], "author": None}
    assert singer_weights(run) == {"a/x": 6 / 8, "b/y": 2 / 8}


def test_nothing_generated_falls_back_to_equal_weights():
    run = fake_run("r", ["a/x", "b/y"], chorus="fixed")
    for k in ("opening", "exchange", "ending"):
        run["parts"][k]["author"] = "fixed"
    assert singer_weights(run) == {"a/x": 0.5, "b/y": 0.5}


def test_group_key_splits_settings_that_change_outcomes():
    base = fake_run("r", ["a/x", "b/y"])
    assert group_key(base) == group_key(fake_run("s", ["a/x", "b/y"]))
    for extra in ({"tolerance": 1}, {"max_retries": 1}, {"temperature": 0.7}, {"effort": "high"},
                  {"gates": ["structure"]}):
        assert group_key(base) != group_key(fake_run("s", ["a/x", "b/y"], **extra))
    # Retries and gates only matter to strict songs.
    free = fake_run("r", ["a/x", "b/y"], track="freeform")
    assert group_key(free) == group_key(fake_run("s", ["a/x", "b/y"], track="freeform", max_retries=1))
    old = fake_run("r", ["a/x", "b/y"])
    assert group_key(old) == group_key(fake_run("s", ["a/x", "b/y"], tolerance=0, max_retries=3))


def test_win_rate_ignores_games_where_the_model_has_equal_credit(tmp_path, monkeypatch):
    a_wins(monkeypatch)

    def board(runs, name):
        out = leaderboard(runs, None, "j/judge", tmp_path / name, bootstrap=0)
        return {r["model"]: r for r in out["table"]}

    # c writes a quarter of both songs: no game, and nothing to rank c by.
    rows = board([fake_run("r1", ["a/x", "c/z"]), fake_run("r2", ["b/y", "c/z"])], "1")
    assert "c/z" not in rows
    assert rows["a/x"]["games"] == 1 and rows["a/x"]["win_rate"] == 1.0
    assert rows["b/y"]["win_rate"] == 0.0
    # A model on both sides is credited to the side where it writes more.
    rows = board([fake_run("r1", ["a/x", "c/z"]), fake_run("r2", ["c/z", "a/x"])], "2")
    assert rows["a/x"]["games"] == 1 and rows["a/x"]["win_rate"] == 1.0
    assert rows["c/z"]["games"] == 1 and rows["c/z"]["win_rate"] == 0.0
    rows = board([fake_run("r1", ["a/x", "a/x"]), fake_run("r2", ["a/x", "c/z"])], "3")
    assert rows["a/x"]["win_rate"] == 1.0 and rows["c/z"]["win_rate"] == 0.0
    # Equal shares of the generated lines: nothing to credit.
    rows = board([fake_run("r1", ["a/x", "c/z"], chorus="fixed"),
                  fake_run("r2", ["a/x", "b/y"], chorus="fixed")], "4")
    assert "a/x" not in rows and rows["c/z"]["games"] == 1


def test_two_model_permutations_with_equal_shares_warn(tmp_path):
    runs = [fake_run("r1", ["a/x", "b/y"], chorus="fixed"), fake_run("r2", ["b/y", "a/x"], chorus="fixed")]
    judge = Judge()
    out = leaderboard(runs, judge, "j/judge", tmp_path / "c.jsonl")
    assert out["table"] == [] and out["pairs"] == 0 and judge.calls == 0
    assert any("No informative pairs" in w and "--include-self" in w for w in out["warnings"])


def test_single_run_groups_and_same_family_judge_warn(tmp_path):
    runs = [fake_run("r1", ["a/x", "b/y"]), fake_run("r2", ["a/x", "b/y"], tolerance=1)]
    out = leaderboard(runs, Judge(), "a/judge", tmp_path / "c.jsonl")
    assert any("2 of 2 groups have a single run" in w for w in out["warnings"])
    assert any("a/x" in w and "family" in w for w in out["warnings"])


def test_forfeits_never_call_the_judge(tmp_path):
    runs = [fake_run("ok", ["a/x", "b/y"]),
            fake_run("bad", ["b/y", "a/x"], failed="api down"),
            fake_run("bad2", ["a/x", "c/z"], failed="api down")]
    judge = Judge()
    cache = tmp_path / "c.jsonl"
    out = leaderboard(runs, judge, "j/judge", cache, bootstrap=0)
    assert judge.calls == 0 and out["forfeits"] == 3 and out["pairs"] == 3
    assert {r["judge"] for r in out["records"]} == {"forfeit"}
    assert cache.read_text() == ""
    scores = {frozenset((r["a"], r["b"])): r["score_a"] if r["a"] < r["b"] else 1 - r["score_a"]
              for r in out["records"]}
    assert scores[frozenset({"bad", "bad2"})] == 0.5
    wins = {r["a"] if r["score_a"] == 1 else r["b"] for r in out["records"] if r["score_a"] != 0.5}
    assert wins == {"ok"}
    assert out["flip_rate"] is None
    assert max(r["games"] for r in out["table"]) >= 2


def test_judgments_are_cached_and_ignored_across_judge_versions(tmp_path):
    runs = [fake_run("r1", ["a/x", "b/y"]), fake_run("r2", ["b/y", "a/x"])]
    cache = tmp_path / "c.jsonl"
    judge = Judge()
    out = leaderboard(runs, judge, "j/judge", cache, bootstrap=0)
    assert judge.calls == 2 and out["flip_rate"] == 1.0
    leaderboard(runs, judge, "j/judge", cache, bootstrap=0)
    assert judge.calls == 2  # cached
    assert json.loads(cache.read_text().splitlines()[0])["judge_version"] == JUDGE_VERSION
    stale = [dict(json.loads(line), judge_version=JUDGE_VERSION + 1) for line in cache.read_text().splitlines()]
    cache.write_text("\n".join(json.dumps(x) for x in stale) + "\n")
    leaderboard(runs, judge, "j/judge", cache, bootstrap=0)
    assert judge.calls == 4
    assert len(cache.read_text().splitlines()) == 2 * len(stale)  # old lines are kept


def test_flip_rate_counts_disagreeing_votes(tmp_path, monkeypatch):
    votes = iter([["a", "a"], ["a", "b"]])

    def fake(a, b, client, judge):
        v = next(votes)
        return {"a": a["id"], "b": b["id"], "winner": "tie", "score_a": sum(x == "a" for x in v) / 2,
                "votes": v, "judge": judge, "judge_version": JUDGE_VERSION}

    monkeypatch.setattr(lb, "pairwise", fake)
    runs = [fake_run("r0", ["a/x", "b/y"]), fake_run("r1", ["b/y", "a/x"]), fake_run("r2", ["b/y", "a/x"])]
    out = leaderboard(runs, None, "j/judge", tmp_path / "c.jsonl", max_pairs=2, bootstrap=0)
    assert out["flip_rate"] == 0.5


def test_pair_selection_is_balanced_and_prefers_cached(tmp_path, monkeypatch):
    seen = []

    def fake(a, b, client, judge):
        seen.append((a["id"], b["id"]))
        return {"a": a["id"], "b": b["id"], "winner": "a", "score_a": 1.0, "votes": ["a", "a"],
                "judge": judge, "judge_version": JUDGE_VERSION}

    monkeypatch.setattr(lb, "pairwise", fake)
    runs = [fake_run(f"r{i}", ["a/x", "b/y"], chorus=1) for i in range(6)]
    runs += [fake_run(f"s{i}", ["b/y", "a/x"], chorus=1) for i in range(6)]
    cache = tmp_path / "c.jsonl"
    out = leaderboard(runs, None, "j/judge", cache, max_pairs=12, seed=3, bootstrap=0)
    assert out["pairs"] == 12
    per_run = {}
    for a, b in seen:
        for r in (a, b):
            per_run[r] = per_run.get(r, 0) + 1
    assert set(per_run) == {r["id"] for r in runs}
    assert set(per_run.values()) == {2}
    # A rerun with a bigger budget reuses all cached pairs and pays only for the new ones.
    before = len(seen)
    out = leaderboard(runs, None, "j/judge", cache, max_pairs=18, seed=3, bootstrap=0)
    assert out["pairs"] == 18 and len(seen) - before == 6


def test_bootstrap_brackets_the_estimate_and_can_be_disabled(tmp_path, monkeypatch):
    rng = random.Random(7)

    def fake(a, b, client, judge):
        s = 1.0 if rng.random() < 0.7 else 0.0
        return {"a": a["id"], "b": b["id"], "winner": "a", "score_a": s, "votes": ["a", "a"],
                "judge": judge, "judge_version": JUDGE_VERSION}

    monkeypatch.setattr(lb, "pairwise", fake)
    runs = [fake_run(f"r{i}", ["a/x", "a/x"]) for i in range(4)]
    runs += [fake_run(f"s{i}", ["b/y", "b/y"]) for i in range(4)]
    runs += [fake_run(f"t{i}", ["c/z", "c/z"]) for i in range(4)]
    out = leaderboard(runs, None, "j/judge", tmp_path / "c.jsonl", max_pairs=None, bootstrap=50)
    assert out["table"]
    for row in out["table"]:
        assert row["elo_lo"] <= row["elo"] <= row["elo_hi"]
    again = leaderboard(runs, None, "j/judge", tmp_path / "c.jsonl", max_pairs=None, bootstrap=50)
    assert again["table"] == out["table"]
    off = leaderboard(runs, None, "j/judge", tmp_path / "c.jsonl", max_pairs=None, bootstrap=0)
    assert all(r["elo_lo"] is None and r["elo_hi"] is None for r in off["table"])


def test_gate_stats_counts_a_self_duet_once_and_keys_by_spec():
    solo = fake_run("r1", ["a/x", "a/x"])
    solo["turns"][0]["retries"] = 2
    mixed = fake_run("r2", ["a/x", "b/y"], failed="boom")
    rows = gate_stats([solo, mixed])
    assert list(rows[0])[0] == "spec"
    by = {r["model"]: r for r in rows}
    assert by["a/x"]["spec"] == "two_voices"
    assert by["a/x"]["songs"] == 2 and by["a/x"]["failed"] == 1
    assert by["b/y"]["songs"] == 1 and by["b/y"]["failed"] == 1
    assert by["a/x"]["retries_per_song"] == 1.0
    assert by["a/x"]["first_try_pass"] == 1.0
    lone = gate_stats([solo])
    assert lone[0]["songs"] == 1 and lone[0]["failed"] == 0
