"""Export a ranked preference chart: python -m weird_ai_bench.chart --help."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


COLORS = {
    "anthropic": "#ca795e", "openai": "#222222", "google": "#34a853",
    "meta-llama": "#078af4", "x-ai": "#7966d2", "qwen": "#ff7819",
    "deepseek": "#304be8", "mistralai": "#edb12d", "moonshotai": "#16b8bd",
    "meta": "#078af4", "z-ai": "#62666d",
}


def preference(elo: float) -> float:
    """Fitted win probability against a strength-zero (1000 Elo) opponent."""
    z = (float(elo) - 1000) * math.log(10) / 400
    return 100 / (1 + math.exp(-z)) if z >= 0 else 100 * math.exp(z) / (1 + math.exp(z))


def demo_data() -> dict:
    # Fictional contestants: this ordering makes no claims about real models.
    providers = ["anthropic", "openai", "google", "openai", "qwen", "meta-llama",
                 "x-ai", "deepseek", "moonshotai", "google", "mistralai", "qwen"]
    scores = [78, 74, 71, 67, 63, 60, 55, 51, 47, 42, 36, 29]
    table = []
    for i, (provider, score) in enumerate(zip(providers, scores), 1):
        elo = 1000 + 400 * math.log10(score / (100 - score))
        table.append({"model": f"{provider}/Example {i:02}", "elo": elo,
                      "elo_lo": elo - 40, "elo_hi": elo + 40})
    return {"demo": True, "judge": "Example judge", "pairs": 0, "table": table}


def render(data: dict, out: Path, title: str = "weird ai bench parody index",
           brand: str = "weird ai bench") -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    rows = sorted(data.get("table", []), key=lambda r: float(r["elo"]), reverse=True)
    if not rows:
        raise ValueError("leaderboard has no ranked models")
    for row in rows:
        elo = float(row["elo"])
        lo, hi = row.get("elo_lo"), row.get("elo_hi")
        if not math.isfinite(elo):
            raise ValueError("Elo scores must be finite")
        if (lo is None) != (hi is None):
            raise ValueError("each interval needs both endpoints")
        if lo is not None and not (math.isfinite(lo) and math.isfinite(hi) and lo <= hi):
            raise ValueError("invalid interval")
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none"})
    fig = plt.figure(figsize=(max(14, len(rows) * .85), 8.4), facecolor="white")
    fig.text(.06, .92, title, fontsize=30, fontfamily="DejaVu Serif", weight="bold")
    fig.text(.06, .868, "Creative preference in constrained songwriting", fontsize=15)
    is_demo = data.get("demo", False)
    if is_demo:
        fig.text(.94, .965, "DESIGN PREVIEW · SYNTHETIC DATA", ha="right", fontsize=10,
                 color="white", weight="bold", bbox=dict(facecolor="#7d236e", edgecolor="none", pad=8))
    forfeits = data.get("forfeits", 0)
    detail = ("Fictional contestants and scores — layout demonstration only" if is_demo else
              f"{'Judges' if len(data.get('judges') or []) > 1 else 'Judge'}: {data.get('judge', 'unspecified')}  ·  "
              f"{data.get('pairs', 0) - forfeits:,} judged pairs  ·  {forfeits} forfeits")
    fig.text(.06, .815, detail, fontsize=11, color="#737373")
    ax = fig.add_axes([.06, .30, .89, .46])
    ax.set_ylim(0, 100)
    ax.set_xlim(-.65, len(rows) - .35)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.tick_params(axis="both", length=0, labelsize=10, colors="#666666")
    ax.grid(axis="y", linestyle=(0, (2, 4)), color="#d5d5d5", zorder=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    labels = []
    for i, row in enumerate(rows):
        provider, _, name = row["model"].partition("/")
        score = preference(row["elo"])
        color = COLORS.get(provider, "#777d88")
        ax.add_patch(FancyBboxPatch((i - .36, 0), .72, score,
                                   boxstyle="round,pad=0,rounding_size=0.1",
                                   facecolor=color, edgecolor="none", zorder=3))
        ax.text(i, max(4, score * .53), f"{score:.0f}", ha="center", va="center",
                color="white", fontsize=14, weight="bold", zorder=4)
        if row.get("elo_lo") is not None:
            # Percentile intervals need not contain the point estimate.
            lo, hi = preference(row["elo_lo"]), preference(row["elo_hi"])
            ax.vlines(i, lo, hi, color="#333333", linewidth=1.15, zorder=5)
            ax.hlines([lo, hi], i - .09, i + .09, color="#333333", linewidth=1.15, zorder=5)
        display = (data.get("labels") or {}).get(row["model"]) or (name or provider).replace("-", " ")
        labels.append(display + "\n" + provider)
    ax.set_xticks(range(len(rows)), labels, rotation=53, ha="right", color="#252525")
    fig.text(.95, .775, brand, ha="right", color="#777777", fontsize=11, weight="bold")
    fig.text(.06, .09, "Index = estimated win probability (%) against a 1000-Elo reference opponent.",
             fontsize=10, color="#666666")
    intervals = ("Whiskers: illustrative intervals." if is_demo else
                 "Whiskers: 95% bootstrap intervals, conditional on the tested songs.")
    fig.text(.06, .062, intervals + "  Meter accuracy is reported separately.", fontsize=10, color="#666666")
    if data.get("footnote"):
        fig.text(.06, .034, data["footnote"], fontsize=10, color="#666666")
    if data.get("warnings"):
        warning = (next((w for w in data["warnings"] if w.startswith("UNRELIABLE")), None) or
                   ("Judge shares a provider family with some contestants." if
                    any("shares a family" in w for w in data["warnings"]) else
                    "Leaderboard warnings: see the source JSON."))
        fig.text(.95, .02, warning, ha="right", fontsize=9, color="#8b3d22")
    out.parent.mkdir(parents=True, exist_ok=True)
    paths = [out.with_suffix(suffix) for suffix in (".png", ".svg")]
    for path in paths:
        fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)
    return paths


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="leaderboard JSON from --json-out")
    source.add_argument("--demo", action="store_true", help="clearly labeled fictional chart")
    parser.add_argument("--out", type=Path, default=Path("runs/leaderboard-chart"), help="output stem for PNG/SVG")
    parser.add_argument("--title", default="weird ai bench parody index")
    parser.add_argument("--brand", default="weird ai bench", help="watermark in the top right")
    args = parser.parse_args(argv)
    data = demo_data() if args.demo else json.loads(args.input.read_text(encoding="utf-8"))
    try:
        paths = render(data, args.out, args.title, args.brand)
    except ImportError:
        parser.error("install plotting support with: uv sync --extra plot")
    except ValueError as exc:
        parser.error(str(exc))
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
