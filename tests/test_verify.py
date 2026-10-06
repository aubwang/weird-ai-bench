"""Verifier tests on synthetic, independently specified lines."""

from weird_ai_bench.phonetics import tokenize, word_info
from weird_ai_bench.spec import InternalRhymeSpec, LineSpec, RhymeSpec, SectionSpec, describe_line
from weird_ai_bench.verify import analyze_line, internal_rhyme, rhyme_level, verify_section


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


def test_tagged_refrain_allows_repeated_end_word_only_within_its_group():
    lines = ["We walk back home", "You hurry back home"]
    tagged = SectionSpec("chorus", "Chorus", [LineSpec(4, rhyme="A", refrain="R"),
                                               LineSpec(5, rhyme="A", refrain="R")],
                         {"A": RhymeSpec()}, singer=1)
    rep = verify_section(lines, tagged)
    assert rep.gate("rhyme") and rep.lines[1].rhyme_level == "refrain"
    assert rep.scores()["rhyme"] == 1

    tagged.lines[1].refrain = "other"
    assert not verify_section(lines, tagged).gate("rhyme")
    tagged.lines[1].refrain = None
    assert not verify_section(lines, tagged).gate("rhyme")


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


def test_internal_rhyme_word_lengths_and_line_ending():
    rule = InternalRhymeSpec(word_syllables=3, end_word=True)
    assert internal_rhyme("Try GPT then LLC", rule=rule)
    assert internal_rhyme("Try G-P-T then L-L-C (hey)", rule=rule)
    assert not internal_rhyme("Try GPT then GPT", rule=rule)
    assert not internal_rhyme("Try GPT then tea", rule=rule)
    assert not internal_rhyme("The bright light helps GPT", rule=rule)
    assert not internal_rhyme("Try GPT then LLC tonight", rule=rule)
    assert not internal_rhyme("Try GPT <adlib>LLC</adlib>", rule=rule)
    assert internal_rhyme("Try GPT then LLC tonight", rule=InternalRhymeSpec(3))

    sec = SectionSpec("hook", "Hook", [LineSpec(8, internal_rhyme=rule)], {}, singer=1)
    assert verify_section(["Try GPT then LLC"], sec).passed()
    failed = verify_section(["See the bright light then GPT"], sec)
    assert failed.gate("syllables") and not failed.gate("internal_rhyme")
    assert "3-syllable words or acronyms" in failed.errors()[0]
    assert "end of the line" in failed.errors()[0]


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


def test_wrong_count_is_charged_once():
    sec = SectionSpec("couplet", "Couplet", [LineSpec(4, [2, 4]), LineSpec(4, [2, 4], split=[2, 2])],
                      {}, singer=1)
    rep = verify_section(["The sky is bright", "The sky is very bright"], sec)
    s = rep.scores()
    assert s["syllables"] == 0.5 and s["stress"] == 1 and "split" not in s


def test_slack_widens_the_count_and_shows_in_prompts_and_errors():
    loose = LineSpec(7, slack=2)
    assert analyze_line("We walk back home tonight, my friend", loose).syllables_ok  # 8
    assert not analyze_line("We walk back home tonight together, my friend", loose).syllables_ok  # 11
    r = analyze_line("We walk", LineSpec(7), tolerance=1)
    assert (r.under, r.over) == (1, 1)
    longer = LineSpec(4, slack=[0, 2])
    assert analyze_line("We walk back home now", longer).syllables_ok  # 5
    assert not analyze_line("We walk", longer).syllables_ok  # 2
    assert "4 syllables (legacy count range 4 to 6)" in describe_line(longer, 1, {})
    sec = SectionSpec("line", "Line", [loose], {}, singer=1)
    assert "it needs 5 to 9." in verify_section(["We walk back home tonight together, my friend"], sec).errors()[0]
    assert "7 syllables (legacy count range 5 to 9)" in describe_line(loose, 1, {})
