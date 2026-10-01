"""Check the displayed index's relationship to the fitted preference model."""
import math

import pytest

from weird_ai_bench.chart import preference
from weird_ai_bench.leaderboard import to_elo


@pytest.mark.parametrize("strength", [-5, -1, 0, 1, 5])
def test_chart_index_matches_pairwise_probability(strength):
    assert preference(to_elo(strength)) == pytest.approx(100 / (1 + math.exp(-strength)))


def test_chart_index_stays_bounded_for_extreme_ratings():
    assert preference(-1e9) == 0
    assert preference(1e9) == 100


def test_leaderboard_json_export(monkeypatch, tmp_path):
    import json
    from weird_ai_bench.cli import main

    board = {"judge": "example/judge", "pairs": 1, "flip_rate": 0, "forfeits": 0,
             "warnings": [], "table": [{"model": "example/model", "elo": 1000,
             "elo_lo": 950, "elo_hi": 1050, "games": 1, "win_rate": .5}]}
    monkeypatch.setattr("weird_ai_bench.leaderboard.load_runs", lambda paths: [{}, {}])
    monkeypatch.setattr("weird_ai_bench.leaderboard.leaderboard", lambda *a, **kw: board)
    monkeypatch.setattr("weird_ai_bench.cli.OpenRouterClient", lambda **kw: None)
    dest = tmp_path / "export" / "board.json"
    assert main(["leaderboard", str(tmp_path), "--judge", "example/judge",
                 "--json-out", str(dest)]) == 0
    assert json.loads(dest.read_text()) == board
