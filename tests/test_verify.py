"""Verifier tests on synthetic, independently specified lines."""

from songbench.phonetics import tokenize, word_info
from songbench.spec import LineSpec, RhymeSpec, SectionSpec
from songbench.verify import analyze_line, internal_rhyme, rhyme_level, verify_section


def test_syllables_stress_and_annotations():
    spec = LineSpec(4, [2, 4])
    good = analyze_line("The sky is bright [4]", spec)
    assert good.syllables_ok and good.stress_ok
    assert not analyze_line("The sky is very bright", spec).syllables_ok
    assert not analyze_line("The sky is bright", LineSpec(4, [1])).stress_ok
    assert analyze_line("every every", LineSpec(4), {"every": 2}).count == 4


def test_acronyms_numbers_and_dropped_g():
    assert sum(t.info.prons[0].syllables for t in tokenize("RL AGI D-O-I")) == 8
    assert tokenize("GPUs")[0].info.prons[0].syllables == 3
    assert tokenize("nothin'")[0].info.prons[0].syllables == 2
    assert analyze_line("I paid 15 bucks", LineSpec(5)).count == 5


def test_full_slant_and_identical_rhyme():
    assert rhyme_level(word_info("true"), word_info("blue")) == "full"
    assert rhyme_level(word_info("crazy"), word_info("shady"), 2) == "slant"
    assert rhyme_level(word_info("help"), word_info("help")) == "identical"
    assert rhyme_level(word_info("house"), word_info("dog")) == "none"
    for a, b in [("light", "delight"), ("certain", "uncertain"), ("view", "review"), ("right", "write")]:
        assert rhyme_level(word_info(a), word_info(b)) == "same_sound", (a, b)
    for a, b in [("ride", "pride"), ("all", "ball"), ("rain", "brain"), ("sent", "present")]:
        assert rhyme_level(word_info(a), word_info(b)) == "full", (a, b)


def test_slant_scores_fully_and_same_sound_scores_a_little():
    sec = SectionSpec("couplet", "Couplet", [LineSpec(4, rhyme="A"), LineSpec(4, rhyme="A")],
                      {"A": RhymeSpec()}, singer=1)
    slant = verify_section(["The sky is bright", "We say goodbye"], sec)
    assert slant.lines[1].rhyme_level == "slant" and slant.scores()["rhyme"] == 1
    same = verify_section(["We saw the light", "Oh what delight"], sec)
    assert not same.gate("rhyme") and "sounds the same as" in same.rhyme_errors[0]
    assert abs(same.scores()["rhyme"] - 0.1) < 1e-9


def test_repeating_an_earlier_sound_is_caught_past_the_anchor():
    sec = SectionSpec("tercet", "Tercet", [LineSpec(4, rhyme="A")] * 3, {"A": RhymeSpec()}, singer=1)
    rep = verify_section(["We saw the light", "We sang all night", "Oh what delight"], sec)
    assert [l.rhyme_ok for l in rep.lines] == [True, True, False]
    assert rep.lines[2].rhyme_level == "same_sound" and rep.lines[2].rhyme_with == 1
    assert rep.rhyme_errors == ["Line 3 ends on 'delight', which sounds the same as line 1's "
                                "'light'. Lines 1, 2, 3 need a rhyme."]


def test_wrenched_rhyme_on_a_sung_last_syllable():
    assert rhyme_level(word_info("confident"), word_info("tent")) == "slant"
    assert rhyme_level(word_info("button"), word_info("cat")) == "none"
    # A one-syllable effect never satisfies a two-syllable rhyme.
    assert rhyme_level(word_info("confident"), word_info("tent"), 2) == "none"


def test_mosaic_rhyme_with_a_trailing_pronoun():
    sec = SectionSpec("couplet", "Couplet", [LineSpec(5, rhyme="A"), LineSpec(5, rhyme="A")],
                      {"A": RhymeSpec(min_syllables=2)}, singer=1)
    assert verify_section(["The night was lonely", "Come on and show me"], sec).gate("rhyme")
    assert not verify_section(["The night was lonely", "Come on and hold it"], sec).gate("rhyme")


def test_rhyme_groups_and_missing_lines():
    sec = SectionSpec("couplet", "Couplet", [LineSpec(4, rhyme="A"), LineSpec(4, rhyme="A")],
                      {"A": RhymeSpec(slant=False)}, singer=1)
    assert verify_section(["The sky is bright", "We watch the light"], sec).passed()
    bad = verify_section(["The sky is bright", "We walk back home"], sec)
    assert not bad.gate("rhyme") and bad.rhyme_errors
    missing = verify_section(["The sky is bright"], sec)
    assert not missing.gate("structure") and missing.scores()["syllables"] < 1


def test_internal_rhyme_and_split():
    assert internal_rhyme("A bright light")
    assert not internal_rhyme("The model is broken")
    spec = LineSpec(4, split=[2, 2])
    assert analyze_line("The sky, is bright", spec).split_ok
    assert not analyze_line("The sky is bright", spec).split_ok


def test_hook_repetition():
    sec = SectionSpec("refrain", "Refrain", [LineSpec(4, hook=True), LineSpec(5, repeats_hook=True)], {}, sung_by="both")
    assert verify_section(["We walk back home", "Now we walk back home"], sec).passed()
    assert not verify_section(["We walk back home", "Now we take the train"], sec).gate("structure")


def test_adlibs_excluded_from_all_line_checks():
    sec = SectionSpec("couplet", "Couplet", [LineSpec(4, [2, 4], rhyme="A", hook=True),
                      LineSpec(4, [2, 4], rhyme="A")], {"A": RhymeSpec(slant=False)}, singer=1)
    plain = ["The sky is bright", "We watch the light"]
    tagged = [line + " <adlib>unrelated extraordinary words</adlib>" for line in plain]
    a, b = verify_section(plain, sec), verify_section(tagged, sec)
    assert b.passed() and a.scores() == b.scores()
    assert analyze_line("The <adlib>oh hey</adlib> sky is bright", LineSpec(4, [2, 4])).stress_ok
    assert analyze_line("<adlib>oh</adlib>", LineSpec(1)).count == 0
    assert analyze_line("We walk home (home)", LineSpec(3)).count == 3
    assert analyze_line("(This is sung)", LineSpec(3)).count == 3
    assert not internal_rhyme("The model is broken <adlib>team dream</adlib>")
    assert not analyze_line("The sky <adlib>,</adlib> is bright", LineSpec(4, split=[2, 2])).split_ok
