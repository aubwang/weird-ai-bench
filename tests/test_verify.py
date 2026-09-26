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
