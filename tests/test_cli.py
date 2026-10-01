import json

from weird_ai_bench.cli import main
from weird_ai_bench.llm import LLMError, ScriptedClient


class SeedClient(ScriptedClient):
    seed = None
    seeds: list = []

    def complete(self, model, messages):
        SeedClient.seeds.append(self.seed)
        return super().complete(model, messages)


def test_matrix_gives_each_sample_its_own_seed(monkeypatch, tmp_path):
    SeedClient.seeds = []
    monkeypatch.setattr("weird_ai_bench.cli._client", lambda args: SeedClient())
    main(["matrix", "--models", "a/x,b/y", "--tracks", "freeform", "--samples", "3",
          "--seed", "5", "--workers", "1", "--out", str(tmp_path)])
    runs = [json.loads(p.read_text()) for p in tmp_path.glob("*.json")]
    assert len(runs) == 6
    by_cast: dict = {}
    for r in runs:
        by_cast.setdefault(tuple(r["config"]["models"]), set()).add(r["config"]["seed"])
    assert all(seeds == {5, 6, 7} for seeds in by_cast.values())
    assert set(SeedClient.seeds) == {5, 6, 7}


class FailingClient(ScriptedClient):
    def complete(self, model, messages):
        if len(self.calls) >= 1:
            raise LLMError(f"{model} used all tokens before answering")
        return super().complete(model, messages)


def test_failed_songs_are_saved(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("weird_ai_bench.cli._client", lambda args: FailingClient())
    assert main(["run", "--model", "a/x", "--model", "b/y", "--track", "freeform",
                 "--out", str(tmp_path)]) == 1
    (run,) = [json.loads(p.read_text()) for p in tmp_path.glob("*.json")]
    assert "used all tokens" in run["failed"]["error"]
    assert run["scores"]["strict_pass"] is False
    assert main(["stats", str(tmp_path)]) == 0
    assert "failed" in capsys.readouterr().out
