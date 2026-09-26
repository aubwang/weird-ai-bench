"""songbench command line."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .llm import LLMError, OpenRouterClient
from .orchestrate import (
    CHORUS, MODES, NAMES, TRACKS, ConfigError, Duet, RunConfig, render_sheet, save,
)
from .prompts import chorus_task, render_song_so_far, section_task, trade_line_task
from .spec import bundled_specs, describe_section, load_spec
from .verify import GATES, verify_section


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _client(args) -> OpenRouterClient:
    return OpenRouterClient(temperature=args.temperature, max_tokens=args.max_tokens,
                            effort=args.effort, seed=args.seed)


def _config(args, model_1=None, model_2=None, mode=None, track=None) -> RunConfig:
    return RunConfig(
        model_1=model_1 or args.model_1, model_2=model_2 or args.model_2,
        mode=mode or args.mode, names=args.names,
        persona_1=getattr(args, "persona_1", None), persona_2=getattr(args, "persona_2", None),
        chorus=args.chorus, presets=args.preset, track=track or args.track,
        max_retries=args.retries, tolerance=args.tolerance,
        gates=[g.strip() for g in args.gates.split(",") if g.strip()],
        spec=args.spec,
        temperature=args.temperature, effort=args.effort, seed=args.seed,
    )


def _common(p: argparse.ArgumentParser, single: bool = True) -> None:
    if single:
        p.add_argument("--mode", choices=MODES, default="each_other")
        p.add_argument("--track", choices=TRACKS, default="strict")
    p.add_argument("--names", choices=NAMES, default="real")
    p.add_argument("--chorus", choices=CHORUS, default="auto",
                   help="auto: use a preset chorus if supplied, otherwise model_1; "
                        "original: source chorus in the song YAML; model_1/model_2: generate it")
    p.add_argument("--preset", action="append", default=[],
                   help="prewritten sections YAML file or bundled ID; repeat for multiple presets")
    p.add_argument("--retries", type=int, default=3, help="strict track: retries per part")
    p.add_argument("--tolerance", type=int, default=0, help="allowed syllable miss per line")
    p.add_argument("--gates", default=",".join(GATES),
                   help=f"strict track: checks that must pass (default: all of {','.join(GATES)})")
    p.add_argument("--spec", default="two_voices", help="bundled spec id or a YAML path")
    p.add_argument("--temperature", type=float)
    p.add_argument("--effort", choices=["minimal", "low", "medium", "high"],
                   help="reasoning effort, for models that support it")
    p.add_argument("--seed", type=int)
    p.add_argument("--max-tokens", type=int, default=8000)
    p.add_argument("--out", default="runs", help="directory for transcripts")
    p.add_argument("--judge", help="judge model id; scores each song after it's written")


def cmd_run(args) -> int:
    cfg = _config(args)
    try:
        duet = Duet(cfg, None)
    except (ConfigError, ValueError, OSError) as e:
        _log(f"error: {e}")
        return 2
    if args.dry_run:
        spec = duet.spec
        for s in (1, 2):
            print(f"===== system prompt, singer {s} =====\n{duet.threads[s][0]['content']}\n")
        first = next((k for k in spec.generation_order if k not in duet.written), None)
        if first is not None:
            sec = spec.sections[first]
            so_far = render_song_so_far(spec, cfg, duet.written, duet.authors)
            task = (chorus_task(spec, sec, so_far) if sec.is_chorus else
                    trade_line_task(spec, cfg, sec, 0, so_far) if sec.is_trade else
                    section_task(spec, cfg, sec, so_far))
            print(f"===== first task =====\n{task}")
        return 0
    try:
        client = _client(args)
        duet.client = client
        _log(f"{cfg.model_1} x {cfg.model_2} · {cfg.mode} · {cfg.names} · "
             f"chorus {cfg.chorus} · {cfg.track}")
        duet.log = _log
        result = duet.run()
        # Preserve paid generation even if optional judging fails.
        jp, mp = save(result, args.out)
        _log(f"saved {jp} and {mp}")
        if args.judge:
            from .judge import rubric
            result["judge"] = rubric(result, client, args.judge)
            save(result, args.out)
    except (LLMError, ConfigError) as e:
        _log(f"error: {e}")
        return 1
    print(render_sheet(result))
    return 0


def _run_one(args, cfg: RunConfig) -> dict:
    client = _client(args)
    result = Duet(cfg, client).run()
    save(result, args.out)
    if args.judge:
        from .judge import rubric
        result["judge"] = rubric(result, client, args.judge)
        save(result, args.out)
    return result


def cmd_matrix(args) -> int:
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    modes = [m.strip() for m in args.modes.split(",")]
    tracks = [t.strip() for t in args.tracks.split(",")]
    pairs = [(a, b) for a, b in itertools.product(models, models) if a != b or args.include_self]
    jobs = []
    for (m1, m2), mode, track in itertools.product(pairs, modes, tracks):
        cfg = _config(args, m1, m2, mode, track)
        try:
            cfg.validate()
        except ConfigError as e:
            _log(f"skip {m1} x {m2} {mode}: {e}")
            continue
        jobs += [cfg] * args.samples
    _log(f"{len(jobs)} songs across {len(pairs)} ordered pairs")
    if args.dry_run:
        for c in jobs:
            print(f"{c.model_1} x {c.model_2} · {c.mode} · {c.track}")
        return 0
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, failures = [], 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_run_one, args, RunConfig(**vars(c))): c for c in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            c = futs[f]
            try:
                r = f.result()
            except Exception as e:  # keep the sweep going
                failures += 1
                _log(f"[{i}/{len(jobs)}] FAILED {c.model_1} x {c.model_2} {c.mode} {c.track}: {e}")
                continue
            b = r["scores"]["by_singer"]
            row = {"id": r["id"], "model_1": c.model_1, "model_2": c.model_2, "mode": c.mode,
                   "names": c.names, "chorus": r["config"]["chorus"], "track": c.track,
                   "adherence_1": b["1"]["adherence"], "adherence_2": b["2"]["adherence"],
                   "first_try_1": b["1"]["first_try_pass_rate"],
                   "first_try_2": b["2"]["first_try_pass_rate"],
                   "strict_pass": r["scores"]["strict_pass"], "cost": r["usage"]["cost"],
                   "judge_overall": r.get("judge", {}).get("scores", {}).get("overall")}
            rows.append(row)
            _log(f"[{i}/{len(jobs)}] {c.model_1} x {c.model_2} {c.mode} {c.track} done")
    if rows:
        csv_path = out / "matrix.csv"
        new = not csv_path.exists()
        with csv_path.open("a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            if new:
                w.writeheader()
            w.writerows(rows)
        _log(f"wrote {len(rows)} rows to {csv_path}")
    return 1 if failures else 0


def cmd_check(args) -> int:
    spec = load_spec(args.spec)
    text = Path(args.file).read_text() if args.file != "-" else sys.stdin.read()
    sections: dict[str, list[str]] = {}
    current = args.section
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("[") and s.endswith("]") and s[1:-1].strip().lower() in spec.sections:
            current = s[1:-1].strip().lower()
            continue
        if s and current:
            sections.setdefault(current, []).append(s)
    if not sections:
        _log("error: give --section, or mark sections with lines like [verse1]")
        return 2
    hook = sections.get(spec.chorus_key() or "", [None])[0]
    ok = True
    for key, lines in sections.items():
        sec = spec.sections[key]
        rep = verify_section(lines, sec, spec.syllable_overrides, args.tolerance, hook=hook)
        print(f"== {sec.label} ==")
        for l in rep.lines:
            marks = [f"{l.count}/{l.target} syl" + ("" if l.syllables_ok else " ✗")]
            if l.stress_required:
                marks.append(f"stress {l.stress_hits}/{l.stress_required}" + ("" if l.stress_ok else " ✗"))
            if l.rhyme_ok is not None:
                marks.append(f"rhyme {l.rhyme_group}: {l.rhyme_level}" + ("" if l.rhyme_ok else " ✗"))
            if l.split_ok is not None:
                marks.append("split ok" if l.split_ok else "split ✗")
            if l.internal_ok is not None:
                marks.append("internal rhyme ok" if l.internal_ok else "internal rhyme ✗")
            if l.guessed_words:
                marks.append("guessed: " + ", ".join(l.guessed_words))
            print(f"{l.index:>2}. {l.text}\n    " + " · ".join(marks))
        errs = rep.errors(GATES)
        if errs:
            ok = False
            print("Issues:\n" + "\n".join(f"  - {e}" for e in errs))
        print(f"Adherence: {rep.scores()['overall']:.0%}\n")
    return 0 if ok else 1


def cmd_judge(args) -> int:
    from .judge import rubric
    client = OpenRouterClient(max_tokens=args.max_tokens)
    for p in args.runs:
        r = json.loads(Path(p).read_text())
        r["judge"] = rubric(r, client, args.judge)
        Path(p).write_text(json.dumps(r, indent=2))
        Path(p).with_suffix(".md").write_text(render_sheet(r))
        s = r["judge"]["scores"]
        print(f"{Path(p).name}: overall {s.get('overall')}  " +
              "  ".join(f"{k} {v}" for k, v in s.items() if k != "overall"))
        if "warning" in r["judge"]:
            _log("warning: " + r["judge"]["warning"])
    return 0


def cmd_stats(args) -> int:
    from .leaderboard import gate_stats, load_runs
    rows = gate_stats(load_runs(args.paths))
    if not rows:
        _log("no runs found")
        return 1
    f = lambda v: "–" if v is None else f"{v:.0%}" if isinstance(v, float) and v <= 1 else f"{v:.2f}" if isinstance(v, float) else str(v)
    print(f"{'model':<40} {'track':<9} {'songs':>5} {'adher.':>7} {'1st-try':>8} {'final':>6} {'retries':>8} {'judge':>6}")
    for r in rows:
        print(f"{r['model']:<40} {r['track']:<9} {r['songs']:>5} {f(r['adherence']):>7} "
              f"{f(r['first_try_pass']):>8} {f(r['final_pass']):>6} "
              f"{'–' if r['retries_per_song'] is None else format(r['retries_per_song'], '.1f'):>8} "
              f"{'–' if r['judge_overall'] is None else format(r['judge_overall'], '.1f'):>6}")
    if args.csv:
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    return 0


def cmd_leaderboard(args) -> int:
    from .leaderboard import leaderboard, load_runs
    runs = load_runs(args.paths)
    if len(runs) < 2:
        _log("need at least two runs")
        return 1
    client = OpenRouterClient(max_tokens=args.max_tokens)
    first = Path(args.paths[0])
    cache = (first if first.is_dir() else first.parent) / "judgments.jsonl"
    lb = leaderboard(runs, client, args.judge, cache, max_pairs=args.max_pairs,
                     seed=args.seed or 0, mix=args.mix, log=_log)
    print(f"Judge: {lb['judge']} · {lb['pairs']} pairwise comparisons\n")
    print(f"{'#':>2}  {'model':<44} {'elo':>5} {'games':>6} {'win%':>6}")
    for i, r in enumerate(lb["table"], 1):
        print(f"{i:>2}  {r['model']:<44} {r['elo']:>5} {r['games']:>6} {r['win_rate']:>6.0%}")
    return 0


def cmd_spec(args) -> int:
    spec = load_spec(args.spec)
    print(f'"{spec.title}" ({spec.artist})\n')
    for key in spec.generation_order:
        print(f"[{key}] " + describe_section(spec.sections[key]) + "\n")
    return 0


def cmd_songs(args) -> int:
    for name in bundled_specs():
        spec = load_spec(name)
        print(f"{name}: {spec.title} ({spec.artist})")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="songbench", description="Parody duet benchmark for LLMs.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="write one duet")
    p.add_argument("--model-1", required=True, help="OpenRouter id for singer 1 (goes first)")
    p.add_argument("--model-2", required=True, help="OpenRouter id for singer 2")
    p.add_argument("--persona-1", help="singer 1's name (names=assigned, or override for real)")
    p.add_argument("--persona-2", help="singer 2's name")
    p.add_argument("--dry-run", action="store_true", help="print the prompts; call nothing")
    _common(p)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("matrix", help="sweep model pairs and settings")
    p.add_argument("--models", required=True, help="comma-separated OpenRouter ids")
    p.add_argument("--modes", default="each_other", help=f"comma list of {','.join(MODES)}")
    p.add_argument("--tracks", default="strict", help=f"comma list of {','.join(TRACKS)}")
    p.add_argument("--samples", type=int, default=1, help="songs per configuration")
    p.add_argument("--include-self", action="store_true", help="also pair each model with itself")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--dry-run", action="store_true", help="list the jobs; call nothing")
    _common(p, single=False)
    p.set_defaults(func=cmd_matrix)

    p = sub.add_parser("check", help="check lyrics you wrote against the spec")
    p.add_argument("file", help="lyrics file, or - for stdin")
    p.add_argument("--section", help="section key, if the file has no [section] headers")
    p.add_argument("--spec", default="two_voices")
    p.add_argument("--tolerance", type=int, default=0)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("judge", help="rubric-score saved runs")
    p.add_argument("runs", nargs="+")
    p.add_argument("--judge", required=True)
    p.add_argument("--max-tokens", type=int, default=8000)
    p.set_defaults(func=cmd_judge)

    p = sub.add_parser("stats", help="gate stats per model (no judge calls)")
    p.add_argument("paths", nargs="+", help="run files or directories")
    p.add_argument("--csv", help="also write the table to this CSV")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("leaderboard", help="pairwise-judge runs and rank models")
    p.add_argument("paths", nargs="+", help="run files or directories")
    p.add_argument("--judge", required=True)
    p.add_argument("--max-pairs", type=int, default=200)
    p.add_argument("--mix", action="store_true", help="compare across settings, not just within")
    p.add_argument("--seed", type=int)
    p.add_argument("--max-tokens", type=int, default=8000)
    p.set_defaults(func=cmd_leaderboard)

    p = sub.add_parser("spec", help="show the song map")
    p.add_argument("--spec", default="two_voices")
    p.set_defaults(func=cmd_spec)

    p = sub.add_parser("songs", help="list bundled song templates; custom YAML files use --spec")
    p.set_defaults(func=cmd_songs)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
