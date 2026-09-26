"""Check lyric lines against a section spec: syllables, stress, rhyme, and more."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .phonetics import VOWELS, Pron, Token, WordInfo, strip_adlibs, tokenize
from .spec import LineSpec, SectionSpec

GATES = ("structure", "syllables", "stress", "split", "rhyme", "internal_rhyme")

# Unstressed words that lean on the word before them at a line end, so the pair
# rhymes as one: "show me" / "lonely".
_ENCLITICS = {"me", "you", "ya", "him", "her", "it", "them", "'em", "us"}

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
    slack: int = 0  # allowed miss either side of the target
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
    rep.slack = max(tolerance, spec.slack)
    rep.syllables_ok = abs(pos - spec.syllables) <= rep.slack
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


def _wrenched(a: Pron, b: Pron) -> bool:
    """Same final consonants, where singing stresses an unstressed last syllable:
    "confident" / "tent". The unstressed vowel must be a reduced one (uh, ih)."""
    if a.guessed or b.guessed:
        return False
    tails = []
    for p in (a, b):
        vi = [i for i, ph in enumerate(p.phones) if ph.rstrip("012") in VOWELS]
        if not vi:
            return False
        v = p.phones[vi[-1]]
        tails.append((v.rstrip("012"), v[-1] == "0", tuple(ph.rstrip("012") for ph in p.phones[vi[-1] + 1:])))
    (va, ua, ca), (vb, ub, cb) = tails
    if not ca or ca != cb or not (ua or ub):
        return False
    return va == vb or (ua and va in ("AH", "IH")) or (ub and vb in ("AH", "IH"))


def _joined(prev: WordInfo, last: WordInfo) -> WordInfo:
    """The last two words as one, the second unstressed: "show me" -> SHOW-mee."""
    prons = []
    for p1 in prev.prons:
        for p2 in last.prons:
            if p1.guessed or p2.guessed:
                continue
            weak = tuple(ph[:-1] + "0" if ph[-1] in "12" else ph for ph in p2.phones)
            prons.append(Pron(p1.phones + weak, p1.stresses + (0,) * p2.syllables))
    return WordInfo(text=f"{prev.text} {last.text}", norm=f"{prev.norm} {last.norm}",
                    prons=prons, weak=False, guessed=False)


def _last_vowel(part: tuple[str, ...]) -> str | None:
    vs = [p for p in part if p in VOWELS]
    return vs[-1] if vs else None


def rhyme_level(a: WordInfo, b: WordInfo, min_syllables: int = 1) -> str:
    """'full', 'slant', 'same_sound', 'identical', or 'none'.

    'same_sound' is a full rhyme whose stressed syllable also starts with the same
    consonants, so it's really one sound: "certain" / "uncertain", "right" / "write".
    """
    if a.norm == b.norm:
        return "identical"
    lv = _sound_level(a, b, min_syllables)
    if lv == "full" and _same_onset(a, b):
        return "same_sound"
    return lv


# Consonant clusters that can start an English syllable, beyond single consonants.
_ONSETS = ({(c, g) for c in "P B T D K G F V TH SH".split() for g in "L R W Y".split()}
           | {("S", c) for c in "P T K M N L W F".split()}
           | {("S", "P", "R"), ("S", "T", "R"), ("S", "K", "R"), ("S", "P", "L"),
              ("S", "K", "W"), ("S", "P", "Y"), ("S", "K", "Y")})


def _onset(phones: tuple[str, ...], v: int) -> tuple[str, ...]:
    """Consonants that start the syllable whose vowel is at index v."""
    i = v
    while i > 0 and phones[i - 1] not in VOWELS:
        i -= 1
    cluster = phones[i:v]
    if i == 0 or len(cluster) <= 1:
        return cluster
    for n in (3, 2):
        if len(cluster) >= n and cluster[-n:] in _ONSETS:
            return cluster[-n:]
    return cluster[-1:]


def _same_onset(a: WordInfo, b: WordInfo) -> bool:
    for pa in a.prons:
        for pb in b.prons:
            if pa.guessed or pb.guessed:
                continue
            fa, fb = (tuple(x.rstrip("012") for x in p.phones) for p in (pa, pb))
            for ra in pa.rhyme_parts():
                if ra in pb.rhyme_parts():
                    va, vb = len(fa) - len(ra), len(fb) - len(ra)
                    if _onset(fa, va) == _onset(fb, vb):
                        return True
    return False


def _sound_level(a: WordInfo, b: WordInfo, min_syllables: int) -> str:
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
            elif min_syllables < 2 and _wrenched(pa, pb):
                best = "slant"
    return best


_RANK = {"full": 2, "slant": 1, "none": 0, "same_sound": 0, "identical": 0}


def rhyme_credit(l: LineReport) -> float | None:
    """Score for a line's end rhyme. Slant counts fully, since the gate accepts it;
    the same sound ("certain" / "uncertain") gets a little."""
    if l.rhyme_ok is None:
        return None
    if l.rhyme_ok:
        return 1.0
    return 0.1 if l.rhyme_level == "same_sound" else 0.0


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
                need = f"{max(l.target - l.slack, 1)} to {l.target + l.slack}" if l.slack else str(l.target)
                out.append(f"{n} (\"{l.text}\") has {l.count} syllables; it needs {need}.")
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
        # Stress and splits depend on the count, so lines with the wrong count skip them
        # rather than lose points a second time.
        counted = [l for l in ls if l.syllables_ok]
        req = sum(l.stress_required for l in counted)
        if req:
            s["stress"] = sum(l.stress_hits for l in counted) / req
        rl = [l for l in ls if l.rhyme_ok is not None]
        if rl:
            s["rhyme"] = sum(rhyme_credit(l) for l in rl) / len(rl)
        sp = [l for l in counted if l.split_ok is not None]
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
    words, ends = {}, {}
    for lr in rep.lines:
        toks = tokenize(lr.text, overrides)
        words[lr.index] = toks[-1].info if toks else None
        # Rhyme candidates: the last word, and with an enclitic, the last two words.
        ends[lr.index] = [t.info for t in toks[-1:]]
        if len(toks) > 1 and toks[-1].info.norm in _ENCLITICS:
            ends[lr.index].append(_joined(toks[-2].info, toks[-1].info))
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
            levels = [rhyme_level(wa, wb, min_syl)
                      for wa in ends.get(a.index, []) for wb in ends.get(b.index, [])]
            if not levels:
                return "none"
            best = max(levels, key=lambda x: _RANK[x])
            if _RANK[best] == 0:
                best = next((x for x in ("same_sound", "identical") if x in levels), best)
            return best

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
        # A line that only repeats an earlier line's sound is weak, whatever the anchor says.
        for i, m in enumerate(members):
            if m.rhyme_ok:
                for e in members[:i]:
                    lv = level(e, m)
                    if lv in ("same_sound", "identical"):
                        m.rhyme_level, m.rhyme_with, m.rhyme_ok = lv, e.index, False
                        break
        bad = [m for m in members if not m.rhyme_ok]
        if bad:
            kind = "a two-syllable rhyme" if min_syl >= 2 else "a rhyme"
            kind += "" if need == 1 else " (full rhyme required)"
            for m in bad:
                if m.rhyme_with is None:
                    continue  # if the anchor fails, every other line fails too and is reported
                w, ow = words.get(m.index), words.get(m.rhyme_with)
                why = {"identical": "repeats the same word as",
                       "same_sound": "sounds the same as"}.get(m.rhyme_level, "doesn't rhyme with")
                rep.rhyme_errors.append(
                    f"Line {m.index} ends on '{w.text if w else ''}', which {why} "
                    f"line {m.rhyme_with}'s '{ow.text if ow else ''}'. Lines "
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
