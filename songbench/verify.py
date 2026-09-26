"""Check lyric lines against a section spec: syllables, stress, rhyme, and more."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .phonetics import VOWELS, Pron, Token, WordInfo, strip_adlibs, tokenize
from .spec import LineSpec, SectionSpec

GATES = ("structure", "syllables", "stress", "split", "rhyme", "internal_rhyme")

# Words that never count toward an internal rhyme (too trivial).
_TRIVIAL = {"i", "my", "me", "you", "we", "he", "she", "it", "they", "a", "the", "so", "oh"}


def _strong(info: WordInfo, pron: Pron, j: int) -> bool:
    """Can syllable j of this word carry a required stress?"""
    if info.weak:
        return False
    if pron.syllables == 1:
        return True  # content monosyllables take stress
    s = pron.stresses[j]
    return s != 0  # 1, 2, or unknown (-1)


@dataclass
class LineReport:
    index: int
    text: str
    target: int
    count: int | None = None
    count_min: int | None = None
    count_max: int | None = None
    syllables_ok: bool = False
    stress_required: int = 0
    stress_hits: int = 0
    stress_issues: list[str] = field(default_factory=list)
    split_ok: bool | None = None
    rhyme_group: str | None = None
    rhyme_level: str | None = None
    rhyme_with: int | None = None
    rhyme_ok: bool | None = None
    internal_ok: bool | None = None
    hook_ok: bool | None = None
    guessed_words: list[str] = field(default_factory=list)

    @property
    def stress_ok(self) -> bool:
        return self.stress_hits == self.stress_required


def analyze_line(text: str, spec: LineSpec, overrides: dict | None = None,
                 tolerance: int = 0, index: int = 1) -> LineReport:
    toks = tokenize(text, overrides)
    rep = LineReport(index=index, text=text, target=spec.syllables)
    rep.guessed_words = [t.info.text for t in toks if t.info.guessed]
    if not toks:
        rep.count = rep.count_min = rep.count_max = 0
        rep.stress_required = len(spec.stress)
        return rep

    required = set(spec.stress)
    split_at = spec.split[0] if spec.split else None

    # DP over words: state (syllable position, split satisfied) -> best
    # (violations, path of (token index, pron, list of weak required beats)).
    states: dict[tuple[int, bool], tuple[int, list]] = {(0, False): (0, [])}
    for ti, tok in enumerate(toks):
        cands: dict[tuple[int, ...], Pron] = {}
        for p in tok.info.prons:
            cands.setdefault(p.stresses, p)
        nxt: dict[tuple[int, bool], tuple[int, list]] = {}
        for (pos, hit), (viol, path) in states.items():
            for pron in cands.values():
                weak_beats = []
                for j in range(pron.syllables):
                    beat = pos + j + 1
                    if beat in required and not _strong(tok.info, pron, j):
                        weak_beats.append(beat)
                npos = pos + pron.syllables
                nhit = hit or (split_at is not None and tok.break_after and npos == split_at)
                key = (npos, nhit)
                cand = (viol + len(weak_beats), path + [(ti, pron, weak_beats)])
                if key not in nxt or cand[0] < nxt[key][0]:
                    nxt[key] = cand
        states = nxt

    positions = sorted({pos for pos, _ in states})
    rep.count_min, rep.count_max = positions[0], positions[-1]

    def rank(item):
        (pos, hit), (viol, _) = item
        return (abs(pos - spec.syllables), 0 if (hit or split_at is None) else 1, viol)

    (pos, hit), (viol, path) = min(states.items(), key=rank)
    rep.count = pos
    rep.syllables_ok = abs(pos - spec.syllables) <= tolerance
    if split_at is not None:
        rep.split_ok = hit and rep.syllables_ok
    rep.stress_required = len(required)
    if rep.syllables_ok or not required:
        rep.stress_hits = len(required) - viol
        for ti, pron, beats in path:
            info = toks[ti].info
            for b in beats:
                if info.weak:
                    rep.stress_issues.append(f"beat {b} lands on '{info.text}', a weak word")
                else:
                    rep.stress_issues.append(f"beat {b} lands on an unstressed syllable of '{info.text}'")
    else:
        rep.stress_hits = 0  # meaningless when the count is off
    return rep


# ---------------------------------------------------------------- rhyme

def _vowel_count(part: tuple[str, ...]) -> int:
    return sum(1 for p in part if p in VOWELS)


def _final_unstressed_tail(p: Pron) -> tuple[str, ...] | None:
    """Last syllable's vowel + coda, if the word has 2+ syllables and it's unstressed."""
    if p.guessed or p.syllables < 2:
        return None
    vi = [i for i, ph in enumerate(p.phones) if ph.rstrip("012") in VOWELS]
    if not vi or p.phones[vi[-1]][-1] != "0":
        return None
    return tuple(ph.rstrip("012") for ph in p.phones[vi[-1]:])


def _last_vowel(part: tuple[str, ...]) -> str | None:
    vs = [p for p in part if p in VOWELS]
    return vs[-1] if vs else None


def rhyme_level(a: WordInfo, b: WordInfo, min_syllables: int = 1) -> str:
    """'full', 'slant', 'identical', or 'none'."""
    if a.norm == b.norm:
        return "identical"
    best = "none"
    for pa in a.prons:
        for pb in b.prons:
            if pa.guessed or pb.guessed:
                ta, tb = "".join(pa.phones), "".join(pb.phones)
                if ta == tb:
                    return "full"
                va = re.match(r"[aeiouy]+", ta)
                vb = re.match(r"[aeiouy]+", tb)
                if va and vb and va.group(0) == vb.group(0):
                    best = "slant"
                continue
            for ra in pa.rhyme_parts():
                for rb in pb.rhyme_parts():
                    if min_syllables >= 2 and (_vowel_count(ra) < 2 or _vowel_count(rb) < 2):
                        continue
                    if ra == rb:
                        return "full"
                    if ra[0] == rb[0] and (min_syllables < 2 or _last_vowel(ra) == _last_vowel(rb)):
                        best = "slant"
            ta, tb = _final_unstressed_tail(pa), _final_unstressed_tail(pb)
            if ta and ta == tb and len(ta) > 1:
                best = "slant"
    return best


_RANK = {"full": 2, "slant": 1, "none": 0, "identical": 0}


def _norm_text(s: str) -> str:
    s = strip_adlibs(s).lower().replace("’", "'")
    return " ".join(re.sub(r"[^\w' ]", " ", s).split())


def internal_rhyme(text: str, overrides: dict | None = None) -> bool:
    toks = [t for t in tokenize(text, overrides)
            if not t.info.weak and t.info.norm not in _TRIVIAL]
    for i in range(len(toks)):
        for j in range(i + 1, len(toks)):
            a, b = toks[i].info, toks[j].info
            if a.norm == b.norm:
                continue
            if rhyme_level(a, b) == "full":
                return True
            ra = set().union(*(p.stressed_rimes() for p in a.prons)) if a.prons else set()
            rb = set().union(*(p.stressed_rimes() for p in b.prons)) if b.prons else set()
            if {r for r in ra & rb if r[1]}:  # shared vowel + consonant
                return True
    return False


# -------------------------------------------------------------- section

@dataclass
class SectionReport:
    section: str
    lines: list[LineReport]
    expected_lines: int
    structure_errors: list[str] = field(default_factory=list)
    rhyme_errors: list[str] = field(default_factory=list)

    def gate(self, name: str) -> bool:
        if name == "structure":
            return not self.structure_errors
        if name == "syllables":
            return all(l.syllables_ok for l in self.lines)
        if name == "stress":
            return all(l.stress_ok for l in self.lines)
        if name == "split":
            return all(l.split_ok is not False for l in self.lines)
        if name == "rhyme":
            return all(l.rhyme_ok is not False for l in self.lines)
        if name == "internal_rhyme":
            return all(l.internal_ok is not False for l in self.lines)
        raise ValueError(name)

    def passed(self, gates=GATES) -> bool:
        return all(self.gate(g) for g in gates)

    def errors(self, gates=GATES) -> list[str]:
        out = []
        if "structure" in gates:
            out += self.structure_errors
        for l in self.lines:
            n = f"Line {l.index}"
            if "syllables" in gates and not l.syllables_ok:
                out.append(f"{n} (\"{l.text}\") has {l.count} syllables; it needs {l.target}.")
            if "stress" in gates and l.syllables_ok and not l.stress_ok:
                out.append(f"{n} (\"{l.text}\"): " + "; ".join(l.stress_issues) + ".")
            if "split" in gates and l.split_ok is False and l.syllables_ok:
                out.append(f"{n} (\"{l.text}\") needs a pause (comma or dash) exactly at the split point.")
            if "internal_rhyme" in gates and l.internal_ok is False:
                out.append(f"{n} (\"{l.text}\") needs an internal rhyme between two of its words.")
        if "rhyme" in gates:
            out += self.rhyme_errors
        return out

    def scores(self) -> dict[str, float]:
        """Adherence per check, 0-1. Missing lines count as failures."""
        n = max(self.expected_lines, 1)
        ls = self.lines
        s: dict[str, float] = {"syllables": sum(l.syllables_ok for l in ls) / n}
        req = sum(l.stress_required for l in ls)
        if req:
            s["stress"] = sum(l.stress_hits for l in ls) / req
        rl = [l for l in ls if l.rhyme_ok is not None]
        if rl:
            pts = sum(1.0 if l.rhyme_level == "full" else 0.75 if l.rhyme_ok else 0.0 for l in rl)
            s["rhyme"] = pts / len(rl)
        sp = [l for l in ls if l.split_ok is not None]
        if sp:
            s["split"] = sum(bool(l.split_ok) for l in sp) / len(sp)
        ir = [l for l in ls if l.internal_ok is not None]
        if ir:
            s["internal_rhyme"] = sum(bool(l.internal_ok) for l in ir) / len(ir)
        s["structure"] = 0.0 if self.structure_errors else 1.0
        s["overall"] = sum(s.values()) / len(s)
        return s

    def to_dict(self) -> dict:
        d = asdict(self)
        d["scores"] = self.scores()
        d["gates"] = {g: self.gate(g) for g in GATES}
        return d


def verify_section(lines: list[str], sec: SectionSpec, overrides: dict | None = None,
                   tolerance: int = 0, upto: int | None = None,
                   hook: str | None = None) -> SectionReport:
    """Verify `lines` against the first `upto` lines of the section spec."""
    specs = sec.lines[: upto or len(sec.lines)]
    rep = SectionReport(section=sec.key, lines=[], expected_lines=len(specs))
    if len(lines) != len(specs):
        rep.structure_errors.append(
            f"{sec.label} needs exactly {len(specs)} lines; got {len(lines)}.")
    for i, (text, ls) in enumerate(zip(lines, specs), 1):
        lr = analyze_line(text, ls, overrides, tolerance, index=i)
        lr.rhyme_group = ls.rhyme
        if ls.internal_rhyme:
            lr.internal_ok = internal_rhyme(text, overrides)
        rep.lines.append(lr)

    # The hook: the chorus's own hook line, or one passed in.
    hook_text = hook
    for lr, ls in zip(rep.lines, specs):
        if ls.hook:
            hook_text = lr.text
    for lr, ls in zip(rep.lines, specs):
        if ls.repeats_hook and hook_text:
            lr.hook_ok = _norm_text(lr.text).endswith(_norm_text(hook_text))
            if not lr.hook_ok:
                rep.structure_errors.append(
                    f"Line {lr.index} must end with the hook (\"{strip_adlibs(hook_text)}\").")

    # Rhyme groups.
    words = {}
    for lr in rep.lines:
        toks = tokenize(lr.text, overrides)
        words[lr.index] = toks[-1].info if toks else None
    groups: dict[str, list[LineReport]] = {}
    for lr, ls in zip(rep.lines, specs):
        if ls.rhyme and not ls.repeats_hook:
            groups.setdefault(ls.rhyme, []).append(lr)
        elif ls.repeats_hook:
            lr.rhyme_ok = None
    for g, members in groups.items():
        rs = sec.rhymes.get(g)
        min_syl = rs.min_syllables if rs else 1
        need = 1 if (rs is None or rs.slant) else 2
        if len(members) < 2:
            continue  # nothing to rhyme with yet (e.g. first bridge line)

        def level(a, b):
            wa, wb = words.get(a.index), words.get(b.index)
            if not wa or not wb:
                return "none"
            return rhyme_level(wa, wb, min_syl)

        # Anchor: the line that rhymes with the most others.
        best_anchor, best_n = members[0], -1
        for cand in members:
            n = sum(_RANK[level(cand, o)] >= need for o in members if o is not cand)
            if n > best_n:
                best_anchor, best_n = cand, n
        for m in members:
            if m is best_anchor:
                # The anchor passes if anything rhymes with it.
                lv = max((level(m, o) for o in members if o is not m), key=lambda x: _RANK[x])
                m.rhyme_level, m.rhyme_with = lv, None
            else:
                lv = level(best_anchor, m)
                m.rhyme_level, m.rhyme_with = lv, best_anchor.index
            m.rhyme_ok = _RANK[m.rhyme_level] >= need
        bad = [m for m in members if not m.rhyme_ok]
        if bad:
            aw = words.get(best_anchor.index)
            kind = "a two-syllable rhyme" if min_syl >= 2 else "a rhyme"
            kind += "" if need == 1 else " (full rhyme required)"
            for m in bad:
                w = words.get(m.index)
                why = "repeats the same word" if m.rhyme_level == "identical" else "doesn't rhyme"
                if m is best_anchor:
                    continue  # if the anchor fails, every other line fails too and is reported
                rep.rhyme_errors.append(
                    f"Line {m.index} ends on '{w.text if w else ''}', which {why} with "
                    f"line {best_anchor.index}'s '{aw.text if aw else ''}'. Lines "
                    f"{', '.join(str(x.index) for x in members)} need {kind}.")
    return rep


def originality(lines: list[str], original_text: str, n: int = 4) -> dict:
    """Word n-gram overlap between generated lines and the original lyrics."""
    def grams(text: str) -> set[tuple[str, ...]]:
        w = _norm_text(text).split()
        return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}

    orig = grams(original_text)
    gen: set[tuple[str, ...]] = set()
    for ln in lines:
        gen |= grams(ln)
    shared = sorted(" ".join(g) for g in gen & orig)
    return {"n": n, "overlap": (len(gen & orig) / len(gen)) if gen else 0.0, "shared": shared}
