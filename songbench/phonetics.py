"""Pronunciation lookup: syllables, stress, and rhyme parts for sung words.

Built on the CMU Pronouncing Dictionary (via `pronouncing`), with handling
for the things lyrics do that dictionaries don't: dropped g's ("nothin'"),
acronyms sung letter by letter ("RL", "AGI"), hyphenated compounds, numbers,
and AI-industry words. Unknown words fall back to a spelling-based estimate
and are flagged so reports can say the check was a guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import pronouncing

VOWELS = {
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
}

LETTERS = {
    "a": "EY1", "b": "B IY1", "c": "S IY1", "d": "D IY1", "e": "IY1",
    "f": "EH1 F", "g": "JH IY1", "h": "EY1 CH", "i": "AY1", "j": "JH EY1",
    "k": "K EY1", "l": "EH1 L", "m": "EH1 M", "n": "EH1 N", "o": "OW1",
    "p": "P IY1", "q": "K Y UW1", "r": "AA1 R", "s": "EH1 S", "t": "T IY1",
    "u": "Y UW1", "v": "V IY1", "w": "D AH1 B AH0 L Y UW0", "x": "EH1 K S",
    "y": "W AY1", "z": "Z IY1",
}

# Always sung letter by letter, even when the dictionary has a word reading.
ACRONYMS = {
    "rl", "agi", "asi", "gpt", "llm", "gpu", "tpu", "doi", "rlhf", "sft",
    "ml", "nlp", "ui", "ux", "sdk", "cli", "mcp", "pr", "qa", "vc", "ipo",
    "ceo", "cto", "api", "ai", "iou", "url", "pdf", "html", "cpu",
    "gpus", "llms", "tpus",
}

# Words the dictionary lacks or gets wrong for this domain.
EXTRA = {
    "openai": ["OW1 P AH0 N EY2 AY1"],
    "anthropic": ["AE0 N TH R AA1 P IH0 K"],
    "chatgpt": ["CH AE1 T JH IY2 P IY2 T IY1"],
    "deepseek": ["D IY1 P S IY2 K"],
    "gemini": ["JH EH1 M AH0 N AY2"],
    "llama": ["L AA1 M AH0"],
    "grok": ["G R AA1 K"],
    "copilot": ["K OW1 P AY2 L AH0 T"],
    "chatbot": ["CH AE1 T B AA2 T"],
    "chatbots": ["CH AE1 T B AA2 T S"],
    "benchmaxxing": ["B EH1 N CH M AE2 K S IH0 NG"],
    "hallucinate": ["HH AH0 L UW1 S AH0 N EY2 T"],
    "hallucinating": ["HH AH0 L UW1 S AH0 N EY2 T IH0 NG"],
    "sycophant": ["S IH1 K AH0 F AH0 N T"],
    "sycophancy": ["S IH1 K AH0 F AH0 N S IY0"],
    "tokenizer": ["T OW1 K AH0 N AY2 Z ER0"],
    "prompt": ["P R AA1 M P T"],
    "prompts": ["P R AA1 M P T S"],
    "emdash": ["EH1 M D AE2 SH"],
    "lotta": ["L AA1 T AH0"],
    "outta": ["AW1 T AH0"],
    "kinda": ["K AY1 N D AH0"],
    "tryna": ["T R AY1 N AH0"],
}

# Unstressed function words: never allowed on a required stressed beat.
WEAK_WORDS = {
    "the", "a", "an", "of", "to", "in", "on", "at", "by", "for", "from",
    "with", "and", "or", "nor", "as", "than", "if", "is", "am", "are", "was",
    "were", "be", "been", "its", "it's", "'s", "da", "de", "uh", "um",
}

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def number_words(n: int) -> list[str]:
    """Spell an integer the way it would usually be sung."""
    if n < 20:
        return [ONES[n]]
    if n < 100:
        t, o = divmod(n, 10)
        return [TENS[t]] + ([ONES[o]] if o else [])
    if 1100 <= n <= 2099 and n % 100 != 0 and not (2000 <= n <= 2009):
        hi, lo = divmod(n, 100)  # years: "twenty twenty-three"
        return number_words(hi) + (["oh"] + number_words(lo) if lo < 10 else number_words(lo))
    if n < 1000:
        h, r = divmod(n, 100)
        return [ONES[h], "hundred"] + (number_words(r) if r else [])
    if n < 1_000_000:
        th, r = divmod(n, 1000)
        return number_words(th) + ["thousand"] + (number_words(r) if r else [])
    return ["a", "lot"]


@dataclass(frozen=True)
class Pron:
    """One pronunciation of a word."""

    phones: tuple[str, ...]
    # Stress per syllable: 1 primary, 2 secondary, 0 unstressed, -1 unknown.
    stresses: tuple[int, ...]
    guessed: bool = False

    @property
    def syllables(self) -> int:
        return len(self.stresses)

    def rhyme_parts(self) -> list[tuple[str, ...]]:
        """Phonemes from a stressed vowel to the end (digits stripped).

        Returns candidates from the last stressed vowel (primary or
        secondary) and from the last primary vowel, most specific first.
        """
        if self.guessed:
            return [self.phones]
        idxs = [i for i, p in enumerate(self.phones) if p[-1] in "12"]
        prim = [i for i, p in enumerate(self.phones) if p[-1] == "1"]
        out = []
        for group in (idxs, prim):
            if group:
                part = tuple(_strip(p) for p in self.phones[group[-1]:])
                if part not in out:
                    out.append(part)
        if not out:  # no stress marks at all: use the last vowel
            vi = [i for i, p in enumerate(self.phones) if _strip(p) in VOWELS]
            if vi:
                out.append(tuple(_strip(p) for p in self.phones[vi[-1]:]))
        return out

    def stressed_rimes(self) -> set[tuple[str, ...]]:
        """(vowel, next consonant) for each stressed syllable; for internal rhyme."""
        if self.guessed:
            return set()
        rimes = set()
        ph = [_strip(p) for p in self.phones]
        for i, p in enumerate(self.phones):
            if p[-1] in "12":
                nxt = ph[i + 1] if i + 1 < len(ph) and ph[i + 1] not in VOWELS else ""
                rimes.add((ph[i], nxt))
        return rimes


def _strip(p: str) -> str:
    return p.rstrip("012")


def _pron_from_string(s: str) -> Pron:
    phones = tuple(s.split())
    stresses = tuple(int(p[-1]) for p in phones if p[-1] in "012")
    return Pron(phones, stresses)


def _acronym(word: str) -> Pron:
    letters = [c for c in word.lower() if c.isalpha()]
    phones: list[str] = []
    for i, c in enumerate(letters):
        last = i == len(letters) - 1
        for p in LETTERS[c].split():
            if p[-1] in "12" and not last:
                p = p[:-1] + "2"  # earlier letters get secondary stress
            phones.append(p)
    return _pron_from_string(" ".join(phones))


def _guess(word: str) -> Pron:
    """Spelling-based fallback: count vowel groups; stress unknown."""
    w = word.lower()
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    if w.endswith(("es", "ed")) and n > 1 and not re.search(r"(t|d|s|z|x|ch|sh)e[sd]$", w):
        n -= 1
    n = max(n, 1)
    m = re.search(r"[aeiouy]+[^aeiouy]*$", w)
    tail = tuple(m.group(0)) if m else tuple(w)
    return Pron(tail, tuple([-1] * n), guessed=True)


def _dict_prons(w: str) -> list[Pron]:
    if w in EXTRA:
        return [_pron_from_string(s) for s in EXTRA[w]]
    return [_pron_from_string(s) for s in pronouncing.phones_for_word(w)]


@dataclass
class WordInfo:
    text: str  # as written
    norm: str  # normalized lookup key
    prons: list[Pron]
    weak: bool  # function word: can't take a required stress
    guessed: bool


@lru_cache(maxsize=20000)
def _lookup(norm: str, was_upper: bool) -> tuple[tuple[Pron, ...], bool]:
    w = norm
    if w.isdigit():
        return (), False  # handled by the tokenizer
    if w in ACRONYMS:
        base = w[:-1] if w.endswith("s") and w[:-1] in ACRONYMS else w
        p = _acronym(base)
        if base != w:
            p = Pron(p.phones + ("Z",), p.stresses)
        return (p,), False
    prons = _dict_prons(w)
    if prons:
        return tuple(prons), False
    # All-caps token the dictionary doesn't know: sing it letter by letter.
    if was_upper and len(w) <= 5 and w.isalpha():
        return (_acronym(w),), False
    # Acronym plural like "GPUs" / "LLMs".
    if w.endswith("s") and (w[:-1] in ACRONYMS or (was_upper and len(w) <= 6)):
        p = _acronym(w[:-1])
        return (Pron(p.phones + ("Z",), p.stresses),), False
    # Dropped g: "nothin'" -> "nothing", with a final N instead of NG.
    if w.endswith("in'") or (w.endswith("in") and _dict_prons(w + "g")):
        base = (w[:-1] if w.endswith("'") else w) + "g"
        bp = _dict_prons(base)
        if bp:
            out = []
            for p in bp:
                ph = list(p.phones)
                if ph and ph[-1] == "NG":
                    ph[-1] = "N"
                out.append(Pron(tuple(ph), p.stresses))
            return tuple(out), False
    # Leading apostrophe: "'cause", "'til".
    if w.startswith("'") and len(w) > 1:
        return _lookup(w[1:], was_upper)
    # Possessive / plural the dictionary lacks.
    for suf, add in (("'s", "Z"), ("s", "Z"), ("'", "")):
        if w.endswith(suf) and len(w) > len(suf) + 1:
            bp = _dict_prons(w[: -len(suf)])
            if bp:
                return tuple(Pron(p.phones + ((add,) if add else ()), p.stresses) for p in bp), False
    # No vowels at all ("rl", "llm"): letters.
    if w.isalpha() and not re.search(r"[aeiouy]", w):
        return (_acronym(w),), False
    return (_guess(w),), True


def word_info(text: str, overrides: dict[str, int] | None = None) -> WordInfo:
    raw = text.strip("\"“”‘’.,!?;:()[]{}…*_")
    raw = raw.replace("’", "'").replace("‘", "'")
    norm = raw.lower()
    was_upper = raw.isupper() and len(raw) >= 2
    prons, guessed = _lookup(norm, was_upper)
    prons = list(prons)
    if overrides and norm in overrides:
        want = overrides[norm]
        keep = [p for p in prons if p.syllables == want]
        if keep:
            prons = keep
        elif prons:
            p = prons[0]
            st = (p.stresses + (0,) * want)[:want]
            prons = [Pron(p.phones, st, p.guessed)]
    weak = norm in WEAK_WORDS
    return WordInfo(text=raw, norm=norm, prons=prons, weak=weak, guessed=guessed)


BREAK_CHARS = ",;:—–"


@dataclass
class Token:
    info: WordInfo
    break_after: bool  # punctuation pause after this word


def strip_adlibs(line: str) -> str:
    """Remove parenthesized ad-libs; unwrap a line that is entirely in parentheses."""
    line = re.sub(r"<adlib>.*?</adlib>", " ", line, flags=re.I | re.S)
    s = re.sub(r"\[[^\]]*\]", " ", line).strip()  # "[10]"-style count annotations
    if s.startswith("(") and s.endswith(")") and s.count("(") == 1:
        return s[1:-1].strip()
    return re.sub(r"\([^)]*\)", " ", s).strip()


def tokenize(line: str, overrides: dict[str, int] | None = None) -> list[Token]:
    s = strip_adlibs(line)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("--", "—")
    s = re.sub(r"(\w)\s*[—–]\s*(\w)", r"\1 — \2", s)
    tokens: list[Token] = []
    for chunk in s.split():
        if chunk in ("—", "–", "-"):
            if tokens:
                tokens[-1].break_after = True
            continue
        brk = bool(chunk) and chunk.rstrip("\"'”)")[-1:] in BREAK_CHARS
        core = chunk.strip("\"“”.,!?;:()[]{}…*_—–")
        if core == "&":
            core = "and"
        elif core and not re.search(r"[A-Za-z0-9]", core):
            core = ""  # emoji and stray symbols aren't sung
        if not core:
            if brk and tokens:
                tokens[-1].break_after = True
            continue
        # Hyphenated: letters "D-O-I" become an acronym; compounds split.
        parts = [p for p in core.split("-") if p]
        if len(parts) > 1 and all(len(p) == 1 and p.isalpha() for p in parts):
            parts = ["".join(parts).upper()]
        words: list[str] = []
        for p in parts:
            if p.isdigit():
                words.extend(number_words(int(p)))
            elif re.fullmatch(r"\d+(st|nd|rd|th|s)", p.lower()):
                words.extend(number_words(int(re.match(r"\d+", p).group(0))))
            else:
                words.append(p)
        for i, w in enumerate(words):
            info = word_info(w, overrides)
            if not info.norm:
                continue
            tokens.append(Token(info, brk and i == len(words) - 1))
    return tokens


def last_word(line: str, overrides: dict[str, int] | None = None) -> WordInfo | None:
    toks = tokenize(line, overrides)
    return toks[-1].info if toks else None
