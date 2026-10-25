"""Draft a song template from a plain lyrics file, for the author to review.

Sections come from `[Section]` headers, or from blank-line blocks when there are
none. A repeated block becomes the chorus. Counts, rhymes, and hooks come from the
text; stresses only where the dictionary is unambiguous. Whatever the original
lyrics would fail is dropped, so a draft always passes its own reference.
"""

from __future__ import annotations

import itertools
import json
import re
from collections import Counter
from dataclasses import dataclass, field

from .phonetics import tokenize
from .spec import SongSpec, spec_from_dict
from .verify import line_ends, norm_text, rhyme_level, verify_section

_CHORUS_WORDS = ("chorus", "refrain", "hook")


@dataclass
class _Line:
    reference: str
    syllables: int
    adlibs: list[str] = field(default_factory=list)
    stress: list[int] = field(default_factory=list)
    split: list[int] | None = None
    rhyme: str | None = None
    refrain: str | None = None
    hook: bool = False
    repeats_hook: bool = False
    todos: list[str] = field(default_factory=list)

    def fields(self) -> dict:
        d = {"reference": self.reference, "syllables": self.syllables}
        for k in ("stress", "split", "rhyme", "refrain", "adlibs"):
            if getattr(self, k):
                d[k] = getattr(self, k)
        for k in ("hook", "repeats_hook"):
            if getattr(self, k):
                d[k] = True
        return d


@dataclass
class _Section:
    key: str
    label: str
    lines: list[_Line]
    chorus: bool = False


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "section"


def _blocks(text: str) -> list[tuple[str | None, list[str]]]:
    """(header label, lines) in the order they're sung."""
    blocks: list[tuple[str | None, list[str]]] = []
    label, lines = None, []
    headed = any(re.fullmatch(r"\[[^\]]+\]", s.strip()) for s in text.splitlines())
    for raw in text.splitlines():
        s = raw.strip()
        header = re.fullmatch(r"\[([^\]]+)\]", s)
        if header or (not s and not headed):
            if lines:
                blocks.append((label, lines))
            label, lines = (header.group(1).strip() if header else None), []
        elif s:
            lines.append(s)
    if lines:
        blocks.append((label, lines))
    return blocks


def _split_adlibs(text: str) -> tuple[str, list[str]]:
    """Trailing "(...)" groups are ad-libs; a line wholly in parentheses is sung."""
    adlibs = []
    while (m := re.search(r"\s*\(([^()]+)\)\s*$", text)) and m.start() > 0:
        adlibs.insert(0, m.group(1).strip())
        text = text[:m.start()].rstrip()
    return text, adlibs


def _spelled(word: str, p) -> bool:
    """A letter-by-letter reading, like "us" as U.S., which singing rarely means."""
    return len(word) <= 3 and p.syllables > 1 and all(p.stresses)


def _line(text: str) -> _Line:
    reference, adlibs = _split_adlibs(text)
    toks = tokenize(reference)
    ln = _Line(reference, 0, adlibs)
    pos, breaks = 0, []
    for i, t in enumerate(toks):
        prons = t.info.prons
        p = prons[0]  # the dictionary's first reading
        if t.info.guessed:
            ln.todos.append(f'"{t.info.text}" isn\'t in the dictionary; its count is a guess')
        counts = sorted({q.syllables for q in prons if not _spelled(t.info.norm, q)} | {p.syllables})
        if not t.info.guessed and len(counts) > 1:
            ln.todos.append(f'"{t.info.text}" can be {" or ".join(map(str, counts))} syllables; '
                            f"this counts {p.syllables}")
        if not t.info.weak and not t.info.guessed and p.syllables > 1 and \
                all(len(q.stresses) != p.syllables or q.stresses == p.stresses for q in prons):
            ln.stress += [pos + j + 1 for j, s in enumerate(p.stresses) if s == 1]
        pos += p.syllables
        if t.break_after and i < len(toks) - 1:
            breaks.append(pos)
    ln.syllables = pos
    if len(breaks) == 1 and breaks[0] >= 2 and pos - breaks[0] >= 2:
        ln.split = [breaks[0], pos - breaks[0]]
    return ln


def _level(a: str, b: str) -> str:
    levels = [rhyme_level(x, y) for x in line_ends(tokenize(a)) for y in line_ends(tokenize(b))]
    for lv in ("full", "slant", "identical"):
        if lv in levels:
            return lv
    return "none"


def _rhymes(sec: _Section) -> None:
    """Group line endings that rhyme; identical endings also share a refrain label."""
    groups: list[list[_Line]] = []
    for ln in sec.lines:
        if ln.repeats_hook:
            continue
        for g in groups:
            if _level(g[0].reference, ln.reference) != "none":
                g.append(ln)
                break
        else:
            groups.append([ln])
    letters = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    for g in groups:
        if len(g) < 2:
            continue
        letter = next(letters)
        for ln in g:
            ln.rhyme = letter
        for a, b in itertools.combinations(g, 2):
            if _level(a.reference, b.reference) == "identical":
                a.refrain = b.refrain = a.refrain or _slug(tokenize(a.reference)[-1].info.norm)


def _hooks(sections: list[_Section]) -> None:
    """The chorus line that other lines end with most often becomes the hook."""
    chorus = next((s for s in sections if s.chorus), None)
    if chorus is None:
        return
    def ends_with(ln: _Line, hook: list[str]) -> bool:
        return norm_text(ln.reference).split()[-len(hook):] == hook

    lines = [ln for s in sections for ln in s.lines]
    best, best_key = None, (0, 0)
    for ln in chorus.lines:
        hook = norm_text(ln.reference).split()
        n = sum(other is not ln and ends_with(other, hook) for other in lines)
        # Ties go to the longer line, the more specific hook.
        if len(hook) >= 2 and n and (n, len(hook)) > best_key:
            best, best_key = ln, (n, len(hook))
    if best is None:
        return
    best.hook = True
    hook = norm_text(best.reference).split()
    seen = False
    for s in [chorus] + [s for s in sections if s is not chorus]:
        for ln in s.lines:
            if ln is best:
                seen = True
            elif ends_with(ln, hook) and (s is not chorus or seen):
                ln.repeats_hook = True


def _raw(sections: list[_Section], order: list[str], meta: dict) -> dict:
    chorus = [s.key for s in sections if s.chorus]
    return {
        **meta, "singers": 1,
        "generation_order": chorus + [s.key for s in sections if not s.chorus],
        "performance_order": order,
        "sections": {s.key: {"label": s.label, **({"sung_by": "all"} if s.chorus else {"singer": 1}),
                             "lines": [ln.fields() for ln in s.lines]} for s in sections},
    }


def _settle(sections: list[_Section], order: list[str], meta: dict) -> SongSpec:
    """Drop whatever the reference lyrics fail, until every section passes."""
    for _ in range(20):
        spec = spec_from_dict(_raw(sections, order, meta))
        hook = next((ln.reference for s in sections for ln in s.lines if ln.hook), None)
        clean = True
        for s in sections:
            rep = verify_section([ln.reference for ln in s.lines], spec.sections[s.key], hook=hook)
            if rep.passed():
                continue
            clean = False
            for lr, ln in zip(rep.lines, s.lines):
                if not lr.syllables_ok:
                    ln.syllables = lr.count
                if not lr.meter_passed(["stress"]):
                    ln.stress = []
                elif not lr.meter_passed(["syllables", "stress", "split"]):
                    ln.split = None
                if lr.split_ok is False:
                    ln.split = None
                if lr.rhyme_ok is False:
                    ln.rhyme = ln.refrain = None
                if lr.hook_ok is False:
                    ln.repeats_hook = False
            counts = Counter(ln.rhyme for ln in s.lines if ln.rhyme)
            for ln in s.lines:
                if ln.rhyme and counts[ln.rhyme] < 2:
                    ln.rhyme = ln.refrain = None
        if clean:
            return spec
    raise RuntimeError("draft didn't settle; please report the lyrics that caused it")


def draft(text: str, title: str, artist: str = "", song_id: str | None = None) -> tuple[str, SongSpec]:
    """The draft template as commented YAML, and the spec it loads as."""
    blocks = _blocks(text)
    if not blocks:
        raise ValueError("no lyrics found")
    # Identical blocks are one section sung again.
    unique: dict[tuple[str, ...], int] = {}
    labels: list[str | None] = []
    texts: list[list[str]] = []
    sung: list[int] = []
    for label, lines in blocks:
        lines = [ln for ln in lines if tokenize(_split_adlibs(ln)[0])]  # skip "♪" and the like
        if not lines:
            continue
        norm = tuple(norm_text(ln) for ln in lines)
        if norm not in unique:
            unique[norm] = len(texts)
            labels.append(label)
            texts.append(lines)
        sung.append(unique[norm])

    counts = Counter(sung)
    named = [i for i, label in enumerate(labels)
             if label and any(w in label.lower() for w in _CHORUS_WORDS)]
    repeated = [i for i in range(len(texts)) if counts[i] > 1]
    chorus = (max(repeated, key=lambda i: (counts[i], i in named)) if repeated else
              named[0] if named else None)

    headed = any(labels)
    secs, verse = [], 0
    for i, (label, lines) in enumerate(zip(labels, texts)):
        if label is None:
            verse += i != chorus
            label = "Intro" if headed else "Chorus" if i == chorus else f"Verse {verse}"
        key, n = _slug(label), 1
        while key in {s.key for s in secs}:
            n += 1
            key = f"{_slug(label)}_{n}"
        secs.append(_Section(key, label if n == 1 else f"{label} ({n})",
                             [_line(ln) for ln in lines], chorus=i == chorus))
    if not secs:
        raise ValueError("no sung words found")
    order = [secs[i].key for i in sung]
    _hooks(secs)
    for s in secs:
        _rhymes(s)
    meta = {"id": song_id or _slug(title), "title": title, "artist": artist}
    spec = _settle(secs, order, meta)
    return _yaml(secs, _raw(secs, order, meta)), spec


_YAML_WORDS = {"y", "n", "yes", "no", "on", "off", "true", "false", "null"}


def _q(value) -> str:
    """A YAML scalar, quoted only when it has to be."""
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z_][\w-]*", value) and \
            value.lower() not in _YAML_WORDS:
        return value
    return json.dumps(value, ensure_ascii=False)


def _yaml(sections: list[_Section], raw: dict) -> str:
    out = [
        "# Draft from `weird-ai-bench draft`. Check each line against the recording:",
        "# counts, stresses, splits, rhymes, and the hook are read from the text alone.",
        "# For a duet, raise `singers` and give each section a `singer`, `sung_by`, or `trade`.",
        f"id: {_q(raw['id'])}",
        f"title: {_q(raw['title'])}",
        f"artist: {_q(raw['artist'])}",
        "singers: 1",
        f"generation_order: [{', '.join(raw['generation_order'])}]",
        f"performance_order: [{', '.join(raw['performance_order'])}]",
        "sections:",
    ]
    for s in sections:
        out += [f"  {s.key}:", f"    label: {_q(s.label)}"]
        out.append("    sung_by: all" if s.chorus else "    singer: 1")
        out.append("    lines:")
        for ln in s.lines:
            out += [f"      # TODO: {t}" for t in ln.todos]
            items = [f"{k}: {_q(v)}" for k, v in ln.fields().items()]
            out.append("      - " + "\n        ".join(items))
    return "\n".join(out) + "\n"
