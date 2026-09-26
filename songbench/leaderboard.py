"""Aggregate runs: gate stats per model, and a pairwise leaderboard."""

from __future__ import annotations

import itertools
import json
import math
import random
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from .judge import pairwise
from .spec import result_spec


def load_runs(paths: list[str]) -> list[dict]:
    files: list[Path] = []
    for p in paths:
        pp = Path(p)
        files += sorted(pp.glob("*.json")) if pp.is_dir() else [pp]
    runs = []
    for f in files:
        try:
            d = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(d, dict) and d.get("version") == 1 and "parts" in d:
            d["_path"] = str(f)
            runs.append(d)
    return runs


def group_key(run: dict) -> tuple:
    c = run["config"]
    template = json.dumps(asdict(result_spec(run)), sort_keys=True)
    reference = (run.get("reference_lyrics") or {}).get("sha256")
    # Compare the actual supplied chorus, not its path or preset name.
    supplied = tuple((k, tuple(p["lines"])) for k, p in sorted(run["parts"].items())
                     if p.get("author") in ("fixed", "original"))
    return (template, c["mode"], c["names"], c["chorus"], c["track"], reference, supplied)


def gate_stats(runs: list[dict]) -> list[dict]:
    """Per model and track: adherence, first-try pass, retries (no judge needed)."""
    acc: dict[tuple, dict] = defaultdict(lambda: {"adherence": [], "turns": 0, "first": 0,
                                                    "final": 0, "retries": 0, "songs": 0,
                                                    "cost": 0.0, "judge": []})
    for r in runs:
        track = r["config"]["track"]
        for s in ("1", "2"):
            b = r["scores"]["by_singer"][s]
            a = acc[(b["model"], track)]
            a["songs"] += 1
            if b["adherence"] is not None:
                a["adherence"].append(b["adherence"])
            turns = [t for t in r["turns"] if str(t["singer"]) == s]
            a["turns"] += len(turns)
            a["first"] += sum(t["first_try_pass"] for t in turns)
            a["final"] += sum(t["final_pass"] for t in turns)
            a["retries"] += sum(t["retries"] for t in turns)
            if "judge" in r and r["judge"]["scores"].get("overall") is not None:
                a["judge"].append(r["judge"]["scores"]["overall"])
    rows = []
    for (model, track), a in sorted(acc.items()):
        rows.append({
            "model": model, "track": track, "songs": a["songs"],
            "adherence": _mean(a["adherence"]),
            "first_try_pass": a["first"] / a["turns"] if a["turns"] else None,
            "final_pass": a["final"] / a["turns"] if a["turns"] else None,
            "retries_per_song": a["retries"] / a["songs"] if a["songs"] else None,
            "judge_overall": _mean(a["judge"]),
        })
    return rows


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def fit_additive_bt(comparisons: list[tuple[list[str], list[str], float]],
                    l2: float = 0.01, iters: int = 3000, lr: float = 0.05) -> dict[str, float]:
    """Bradley-Terry where a song's strength is the sum of its two models' strengths.

    Each comparison is (models in song A, models in song B, score for A in [0, 1]).
    """
    models = sorted({m for a, b, _ in comparisons for m in a + b})
    s = {m: 0.0 for m in models}
    # Scale the entire gradient, including regularization, so the objective
    # stays the same but the step cannot grow with the number of comparisons.
    step = lr / max(len(comparisons), 1)
    for _ in range(iters):
        g = {m: -2 * l2 * s[m] for m in models}
        for a, b, y in comparisons:
            d = sum(s[m] for m in a) - sum(s[m] for m in b)
            p = 1 / (1 + math.exp(-d)) if d >= 0 else math.exp(d) / (1 + math.exp(d))
            for m in a:
                g[m] += y - p
            for m in b:
                g[m] -= y - p
        for m in models:
            s[m] += step * g[m]
    mean = _mean(list(s.values())) or 0.0
    return {m: v - mean for m, v in s.items()}


def to_elo(s: float) -> float:
    return 1000 + s * 400 / math.log(10)


def leaderboard(runs: list[dict], client, judge_model: str, cache_path: Path,
                max_pairs: int | None = 200, seed: int = 0, mix: bool = False,
                log=None) -> dict:
    log = log or (lambda m: None)
    cache: dict[str, dict] = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            if line.strip():
                c = json.loads(line)
                cache[_ckey(c["judge"], c["a"], c["b"])] = c

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in runs:
        groups[("all",) if mix else group_key(r)].append(r)

    pairs = []
    for g, rs in groups.items():
        for a, b in itertools.combinations(rs, 2):
            ma = sorted([a["config"]["model_1"], a["config"]["model_2"]])
            mb = sorted([b["config"]["model_1"], b["config"]["model_2"]])
            if ma != mb:  # same models on both sides carry no ranking information
                pairs.append((a, b))
    rng = random.Random(seed)
    rng.shuffle(pairs)
    if max_pairs is not None:
        pairs = pairs[:max_pairs]

    comparisons, records = [], []
    with cache_path.open("a") as fh:
        for i, (a, b) in enumerate(pairs, 1):
            key = _ckey(judge_model, a["id"], b["id"])
            if key in cache:
                rec = cache[key]
            else:
                log(f"  judging pair {i}/{len(pairs)}")
                rec = pairwise(a, b, client, judge_model)
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
            y = rec["score_a"] if rec["a"] == a["id"] else 1 - rec["score_a"]
            comparisons.append(([a["config"]["model_1"], a["config"]["model_2"]],
                                [b["config"]["model_1"], b["config"]["model_2"]], y))
            records.append(rec)

    strengths = fit_additive_bt(comparisons) if comparisons else {}
    games: dict[str, list[float]] = defaultdict(list)
    for a, b, y in comparisons:
        for m in set(a):
            games[m].append(y)
        for m in set(b):
            games[m].append(1 - y)
    table = sorted(
        ({"model": m, "elo": round(to_elo(v)), "games": len(games[m]),
          "win_rate": _mean(games[m])} for m, v in strengths.items()),
        key=lambda r: -r["elo"])
    return {"judge": judge_model, "pairs": len(comparisons), "table": table, "records": records}


def _ckey(judge: str, a: str, b: str) -> str:
    x, y = sorted([a, b])
    return f"{judge}|{x}|{y}"
