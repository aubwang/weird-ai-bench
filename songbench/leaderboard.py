"""Aggregate runs: gate stats per model, and a pairwise leaderboard."""

from __future__ import annotations

import heapq
import itertools
import json
import math
import random
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from .judge import JUDGE_VERSION, pairwise
from .llm import family
from .spec import result_spec
from .verify import GATES


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
        if isinstance(d, dict) and d.get("version") == 2 and "parts" in d:
            d["_path"] = str(f)
            runs.append(d)
    return runs


def group_key(run: dict) -> tuple:
    c = run["config"]
    template = json.dumps(asdict(result_spec(run)), sort_keys=True)
    # Compare what the singers were told, not the scenario's id or path.
    sc = run["scenario_snapshot"]
    scenario = json.dumps({"text": sc["text"], "per_singer": sc["per_singer"]}, sort_keys=True)
    reference = (run.get("reference_lyrics") or {}).get("sha256")
    # Compare the actual supplied chorus, not its path or preset name.
    supplied = tuple((k, tuple(p["lines"])) for k, p in sorted(run["parts"].items())
                     if p.get("author") in ("fixed", "original"))
    strict = c["track"] == "strict"
    # Retries and gates only shape strict songs.
    retries = c.get("max_retries", 3) if strict else None
    gates = tuple(sorted(c.get("gates") or GATES)) if strict else None
    return (template, scenario, c["names"], c["chorus"], c["track"], c.get("guidance", "full"),
            reference, supplied, c.get("tolerance", 0), retries, gates,
            c.get("temperature"), c.get("effort"))


def singer_weights(run: dict) -> dict[str, float]:
    """Each model's share of the generated lines as performed (repeats count); sums to 1."""
    spec = result_spec(run)
    cfg = run["config"]
    models = cfg["models"]
    counts: dict[str, int] = defaultdict(int)
    for key in spec.performance_order:
        sec = spec.sections[key]
        author = (run["parts"].get(key) or {}).get("author")
        if author in ("fixed", "original"):
            continue
        if author is None:  # never written (a failed run): use the template's assignment
            if sec.is_chorus:
                c = str(cfg.get("chorus", ""))
                author = int(c) if c.isdigit() else None
            else:
                author = list(sec.trade) if sec.is_trade else sec.singer
        if isinstance(author, list):
            singers = author
        elif isinstance(author, int):
            singers = [author] * len(sec.lines)
        else:
            continue
        for s in singers:
            if isinstance(s, int) and 1 <= s <= len(models):
                counts[models[s - 1]] += 1
    total = sum(counts.values())
    if not total:
        for m in models:
            counts[m] += 1
        total = len(models)
    return {m: n / total for m, n in counts.items()}


def gate_stats(runs: list[dict]) -> list[dict]:
    """Per spec, model, track, and guidance: adherence, first-try pass, retries (no judge needed)."""
    acc: dict[tuple, dict] = defaultdict(lambda: {"adherence": [], "turns": 0, "first": 0,
                                                    "final": 0, "retries": 0, "songs": 0,
                                                    "failed": 0, "judge": []})
    for r in runs:
        cfg = r["config"]
        spec = r.get("spec") or cfg.get("spec")
        slots: dict[str, list[str]] = defaultdict(list)
        for s, b in r["scores"]["by_singer"].items():
            slots[b["model"]].append(s)
        overall = (r.get("judge") or {}).get("scores", {}).get("overall")
        for model, singers in slots.items():
            a = acc[(spec, model, cfg["track"], cfg.get("guidance", "full"))]
            a["songs"] += 1
            a["failed"] += "failed" in r
            for s in singers:
                b = r["scores"]["by_singer"][s]
                if b["adherence"] is not None:
                    a["adherence"].append(b["adherence"])
                turns = [t for t in r["turns"] if str(t["singer"]) == s]
                a["turns"] += len(turns)
                a["first"] += sum(t["first_try_pass"] for t in turns)
                a["final"] += sum(t["final_pass"] for t in turns)
                a["retries"] += sum(t["retries"] for t in turns)
            if overall is not None:
                a["judge"].append(overall)
    rows = []
    for (spec, model, track, guidance), a in sorted(acc.items(), key=lambda kv: tuple(map(str, kv[0]))):
        rows.append({
            "spec": spec, "model": model, "track": track, "guidance": guidance,
            "songs": a["songs"], "failed": a["failed"],
            "adherence": _mean(a["adherence"]),
            "first_try_pass": a["first"] / a["turns"] if a["turns"] else None,
            "final_pass": a["final"] / a["turns"] if a["turns"] else None,
            "retries_per_song": a["retries"] / a["songs"] if a["songs"] else None,
            "judge_overall": _mean(a["judge"]),
        })
    return rows


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def _softplus(d: float) -> float:
    return max(d, 0.0) + math.log1p(math.exp(-abs(d)))


def _cholesky_solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    low = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            v = a[i][j] - sum(low[i][k] * low[j][k] for k in range(j))
            low[i][j] = math.sqrt(v) if i == j else v / low[j][j]
    z = [0.0] * n
    for i in range(n):
        z[i] = (b[i] - sum(low[i][k] * z[k] for k in range(i))) / low[i][i]
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (z[i] - sum(low[k][i] * x[k] for k in range(i + 1, n))) / low[i][i]
    return x


def fit_additive_bt(comparisons: list[tuple[dict[str, float], dict[str, float], float]],
                    weights: list[float] | None = None, prior_sd: float = 1.0) -> dict[str, float]:
    """MAP Bradley-Terry where a song's strength is sum(weight * model strength).

    Each comparison is (credit in song A, credit in song B, score for A in [0, 1]), where credit
    maps a model to its share of the song. `weights` counts each comparison that many times.
    Strengths get a N(0, prior_sd^2) prior, which keeps a perfectly separated pair finite, and
    are solved with Newton's method, so the result doesn't depend on an iteration budget.
    Returned strengths are centered to mean 0.
    """
    weights = weights if weights is not None else [1.0] * len(comparisons)
    rows = []  # (sparse difference vector, score for A, weight)
    for (wa, wb, y), c in zip(comparisons, weights):
        if c <= 0:
            continue
        x = {m: wa.get(m, 0.0) - wb.get(m, 0.0) for m in {*wa, *wb}}
        x = {m: v for m, v in x.items() if v}
        if x:
            rows.append((x, y, c))
    models = sorted({m for x, _, _ in rows for m in x})
    idx = {m: i for i, m in enumerate(models)}
    n = len(models)
    if not n:
        return {}
    prec = 1 / prior_sd ** 2
    rows = [([(idx[m], v) for m, v in x.items()], y, c) for x, y, c in rows]

    def objective(t: list[float]) -> float:
        total = -0.5 * prec * sum(v * v for v in t)
        for x, y, c in rows:
            d = sum(v * t[i] for i, v in x)
            total += c * (y * d - _softplus(d))
        return total

    theta = [0.0] * n
    f = objective(theta)
    for _ in range(100):
        grad = [-prec * v for v in theta]
        hess = [[0.0] * n for _ in range(n)]
        for i in range(n):
            hess[i][i] = prec
        for x, y, c in rows:
            d = sum(v * theta[i] for i, v in x)
            p = 1 / (1 + math.exp(-d)) if d >= 0 else math.exp(d) / (1 + math.exp(d))
            for i, v in x:
                grad[i] += c * (y - p) * v
                for j, u in x:
                    hess[i][j] += c * p * (1 - p) * v * u
        step = _cholesky_solve(hess, grad)
        scale = 1.0
        while scale > 1e-12:
            new = [t + scale * s for t, s in zip(theta, step)]
            f_new = objective(new)
            if f_new >= f - 1e-12:
                break
            scale /= 2
        else:
            break
        theta, f = new, f_new
        if max(abs(scale * s) for s in step) < 1e-9:
            break
    mean = sum(theta) / n
    return {m: theta[idx[m]] - mean for m in models}


def to_elo(s: float) -> float:
    return 1000 + s * 400 / math.log(10)


def _percentile(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    pos = q * (len(xs) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def _wkey(w: dict[str, float]) -> tuple:
    return tuple(sorted((m, round(v, 6)) for m, v in w.items() if round(v, 6)))


def _balanced(cands: list[tuple[int, int]], k: int | None, counts: dict[int, int]) -> list:
    """Greedily take pairs whose two runs have the fewest pairs so far; ties keep shuffle order."""
    if k is None or k >= len(cands):
        for i, j in cands:
            counts[i] += 1
            counts[j] += 1
        return list(cands)
    heap = [(counts[i] + counts[j], n, i, j) for n, (i, j) in enumerate(cands)]
    heapq.heapify(heap)
    chosen = []
    while heap and len(chosen) < k:
        cost, n, i, j = heapq.heappop(heap)
        if cost != counts[i] + counts[j]:  # counts only grow, so refresh and retry
            heapq.heappush(heap, (counts[i] + counts[j], n, i, j))
            continue
        chosen.append((i, j))
        counts[i] += 1
        counts[j] += 1
    return chosen


def _consistent(rec: dict) -> bool | None:
    if rec.get("consistent") is not None:
        return bool(rec["consistent"])
    votes = rec.get("votes") or []
    return len(set(votes)) == 1 if votes else None


def leaderboard(runs: list[dict], client, judge_model: str, cache_path: Path,
                max_pairs: int | None = 200, seed: int = 0, mix: bool = False,
                log=None, bootstrap: int = 200, prior_sd: float = 1.0) -> dict:
    log = log or (lambda m: None)
    cache: dict[str, dict] = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            if c.get("judge_version") == JUDGE_VERSION:
                cache[_ckey(c["judge"], c["a"], c["b"])] = c

    warnings: list[str] = []
    groups: dict[tuple, list[int]] = defaultdict(list)
    for i, r in enumerate(runs):
        groups[("all",) if mix else group_key(r)].append(i)
    weights = [singer_weights(r) for r in runs]
    wkeys = [_wkey(w) for w in weights]
    failed = ["failed" in r for r in runs]

    candidates, same = [], 0
    for idxs in groups.values():
        for i, j in itertools.combinations(idxs, 2):
            if wkeys[i] != wkeys[j]:  # identical credit on both sides carries no ranking information
                candidates.append((i, j))
            else:
                same += 1
    single = sum(len(v) == 1 for v in groups.values())
    if single:
        warnings.append(f"{single} of {len(groups)} groups have a single run, so there is nothing "
                        f"to compare; runs only compare within a group of identical settings.")
    if not candidates and same:
        warnings.append("No informative pairs: every pair of songs in a group has the same models "
                        "with the same share of lines (for example A x B against B x A with a "
                        "supplied chorus), so no comparison says which model is better. Add a third "
                        "model, or use --include-self so single-model songs face mixed ones.")
    elif not candidates and not single:
        warnings.append("No pairs to compare.")
    elif all(set(weights[i]) == set(weights[j]) for i, j in candidates):
        warnings.append("Every compared pair has the same models, differing only in who wrote "
                        "which part (A x B against B x A), so the ranking rests on that alone and "
                        "any advantage of a singer slot leaks into it. Add a third model, or use "
                        "--include-self.")
    all_models = sorted({m for r in runs for m in r["config"]["models"]})
    try:
        from .judge import family_overlap
        overlap = family_overlap(all_models, judge_model)
    except ImportError:
        overlap = [m for m in all_models if family(m) == family(judge_model)]
    if overlap:
        warnings.append(f"Judge {judge_model} shares a family with {', '.join(overlap)}; "
                        f"its rankings may favor those models.")

    rng = random.Random(seed)
    rng.shuffle(candidates)
    free = [(i, j) for i, j in candidates
            if failed[i] or failed[j]
            or _ckey(judge_model, runs[i]["id"], runs[j]["id"]) in cache]
    free_set = set(free)
    paid = [p for p in candidates if p not in free_set]
    counts: dict[int, int] = defaultdict(int)
    pairs = _balanced(free, max_pairs, counts)
    if max_pairs is None or len(pairs) < max_pairs:
        pairs += _balanced(paid, None if max_pairs is None else max_pairs - len(pairs), counts)

    comparisons, records, pair_idx = [], [], []
    with cache_path.open("a") as fh:
        for n, (i, j) in enumerate(pairs, 1):
            a, b = runs[i], runs[j]
            key = _ckey(judge_model, a["id"], b["id"])
            if failed[i] or failed[j]:
                score = 0.5 if failed[i] and failed[j] else 0.0 if failed[i] else 1.0
                rec = {"a": a["id"], "b": b["id"],
                       "winner": "a" if score > 0.5 else "b" if score < 0.5 else "tie",
                       "score_a": score, "votes": [], "judge": "forfeit",
                       "judge_version": JUDGE_VERSION, "consistent": True}
            elif key in cache:
                rec = cache[key]
            else:
                log(f"  judging pair {n}/{len(pairs)}")
                rec = pairwise(a, b, client, judge_model)
                rec.setdefault("judge_version", JUDGE_VERSION)
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
            y = rec["score_a"] if rec["a"] == a["id"] else 1 - rec["score_a"]
            comparisons.append((weights[i], weights[j], y))
            records.append(rec)
            pair_idx.append((i, j))

    strengths = fit_additive_bt(comparisons, prior_sd=prior_sd) if comparisons else {}
    bands = _bootstrap(runs, groups, comparisons, pair_idx, strengths, bootstrap, seed, prior_sd)

    credit: dict[str, list[float]] = defaultdict(list)
    for wa, wb, y in comparisons:
        for m in {*wa, *wb}:
            da, db = round(wa.get(m, 0.0), 6), round(wb.get(m, 0.0), 6)
            if da != db:  # a model on both sides equally is no evidence for or against itself
                credit[m].append(y if da > db else 1 - y)
    table = sorted(
        ({"model": m, "elo": round(to_elo(v)),
          "elo_lo": round(to_elo(bands[m][0])) if m in bands else None,
          "elo_hi": round(to_elo(bands[m][1])) if m in bands else None,
          "games": len(credit[m]), "win_rate": _mean(credit[m]), "strength": v}
         for m, v in strengths.items()),
        key=lambda r: -r["elo"])
    judged = [c for r in records if r.get("judge") != "forfeit" and (c := _consistent(r)) is not None]
    return {"judge": judge_model, "pairs": len(comparisons), "table": table, "records": records,
            "flip_rate": (sum(not c for c in judged) / len(judged)) if judged else None,
            "warnings": warnings,
            "forfeits": sum(r.get("judge") == "forfeit" for r in records)}


def _bootstrap(runs, groups, comparisons, pair_idx, strengths, reps, seed, prior_sd):
    """2.5 and 97.5 percentiles of each model's strength, resampling runs within each group."""
    if not reps or not comparisons:
        return {}
    rng = random.Random(f"{seed}-bootstrap")
    draws: dict[str, list[float]] = defaultdict(list)
    for _ in range(reps):
        counts: dict[int, int] = defaultdict(int)
        for idxs in groups.values():
            for i in rng.choices(idxs, k=len(idxs)):
                counts[i] += 1
        w = [counts[i] * counts[j] for i, j in pair_idx]
        fit = fit_additive_bt(comparisons, w, prior_sd)
        for m in strengths:
            draws[m].append(fit.get(m, 0.0))  # no data in this draw: the prior's mean
    return {m: (_percentile(draws[m], 0.025), _percentile(draws[m], 0.975))
            for m in strengths if draws[m]}


def _ckey(judge: str, a: str, b: str) -> str:
    x, y = sorted([a, b])
    return f"{judge}|v{JUDGE_VERSION}|{x}|{y}"
