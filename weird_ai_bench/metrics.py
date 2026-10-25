"""Additive diagnostic metrics, independent of composite adherence and ranking."""

from collections import Counter

METRICS_VERSION = 1
RATE_METRICS = ("exact_syllables", "syllables", "stress", "phrase", "rhyme")


def line_metrics(report, line_spec, rhyme_required=False):
    """One expected generated slot. None denotes a missing line, not an exemption."""
    settings = line_spec.prosody
    stress = any(s.stress for s in settings) if settings else bool(line_spec.stress)
    phrase = any(s.split for s in settings) if settings else line_spec.split is not None
    present = report is not None and bool(report.text.strip())
    return {
        "exact_syllables": bool(present and report.exact_syllables_ok),
        "syllables": bool(present and report.syllables_ok),
        "stress": bool(present and report.meter_passed(("syllables", "stress"))) if stress else None,
        "phrase": bool(present and report.meter_passed(("syllables", "split"))) if phrase else None,
        "rhyme": bool(present and report.rhyme_ok) if rhyme_required else None,
        "missing": not present,
        "copy_checked": bool(present and report.copied is not None),
        "copied": bool(present and report.copied),
        "guessed_pronunciation": bool(present and report.guessed_words),
    }


def section_metrics(report, section):
    groups = Counter(ls.rhyme for ls in section.lines if ls.rhyme and not ls.repeats_hook)
    return [line_metrics(report.lines[i] if i < len(report.lines) else None, ls,
                         bool(ls.rhyme and not ls.repeats_hook and groups[ls.rhyme] >= 2))
            for i, ls in enumerate(section.lines)]


def summarize_metrics(lines):
    rates = {}
    for name in RATE_METRICS:
        values = [line[name] for line in lines if line[name] is not None]
        passed, total = sum(values), len(values)
        rates[name] = {"passed": passed, "total": total,
                       "rate": passed / total if total else None}
    return {"version": METRICS_VERSION, "expected_lines": len(lines),
            **{name: sum(line[name] for line in lines)
               for name in ("missing", "copy_checked", "copied", "guessed_pronunciation")},
            **rates}
