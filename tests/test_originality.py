"""Copying the original lyrics earns nothing."""

from dataclasses import asdict

from songbench.llm import ScriptedClient
from songbench.orchestrate import RunConfig, Song, reference_lines, rescore
from songbench.spec import LineSpec, SectionSpec, load_spec
from songbench.verify import GATES, SCORING_VERSION, verify_section

REFERENCE = ["We watch the light", "We walk back home", "The sky is bright"]
COPY = ["<lyrics>We watch the light\nWe walk back home</lyrics>",
        "<lyrics>The sky is bright</lyrics>",
        "<lyrics>You take the road</lyrics>", "<lyrics>I take the train</lyrics>",
        "<lyrics>Now we walk back home</lyrics>"]
OWN = ["<lyrics>We chase the dawn\nWe head for town</lyrics>",
       "<lyrics>A moon stays high</lyrics>",
       "<lyrics>Take me along</lyrics>", "<lyrics>I'll meet you there</lyrics>",
       "<lyrics>Now we head for town</lyrics>"]


def section(n_lines=1, syllables=4, **kw):
    return SectionSpec("s", "Section", [LineSpec(syllables, **kw) for _ in range(n_lines)], {}, singer=1)


def test_copying_the_reference_scores_zero_and_fails_strict():
    r = Song(RunConfig(["a/one", "b/two"], max_retries=0), ScriptedClient(list(COPY))).run()
    assert not r["scores"]["strict_pass"]
    assert [r["scores"]["by_singer"][s]["adherence"] for s in "12"] == [0, 0]
    assert all(v["overall"] < 1 for v in r["verification"].values() for v in [v["scores"]])
    assert r["verification"]["refrain"]["gates"]["originality"] is False
    assert r["verification"]["refrain"]["scores"]["originality"] == 0
    assert r["verification"]["refrain"]["scores"]["syllables"] == 0


def test_strict_track_tells_the_model_it_copied():
    client = ScriptedClient([COPY[0], OWN[0], *OWN[1:]])
    r = Song(RunConfig(["a/one", "b/two"]), client).run()
    turn = r["turns"][0]
    assert turn["retries"] == 1 and not turn["first_try_pass"] and turn["final_pass"]
    assert "copies the original lyrics" in client.calls[1]["messages"][-1]["content"]
    assert r["scores"]["strict_pass"]


def test_freeform_copy_is_scored_but_not_retried():
    r = Song(RunConfig(["a/one", "b/two"], track="freeform"), ScriptedClient(list(COPY))).run()
    assert not r["scores"]["strict_pass"] and r["scores"]["by_singer"]["1"]["adherence"] == 0


def test_unguided_runs_score_originality_too():
    r = Song(RunConfig(["a/one", "b/two"], track="freeform", guidance="none"),
             ScriptedClient(list(COPY))).run()
    assert r["scores"]["by_singer"]["1"]["adherence"] == 0
    r = Song(RunConfig(["a/one", "b/two"], track="freeform", guidance="none"),
             ScriptedClient(list(OWN))).run()
    assert r["scores"]["strict_pass"] and r["scores"]["by_singer"]["1"]["adherence"] == 1


def test_borrowing_a_short_phrase_is_fine():
    sec = section(syllables=9)
    line = "Tonight beneath the stars we walk back home slowly"
    rep = verify_section([line], sec, reference=REFERENCE)
    assert rep.lines[0].copied is False and rep.gate("originality")
    assert verify_section(["Now we walk back home"], section(5), reference=REFERENCE).lines[0].copied
    assert not verify_section(["We walk back"], section(3), reference=REFERENCE).lines[0].copied


def test_copy_ignores_case_punctuation_and_adlibs():
    rep = verify_section(["the SKY is bright! <adlib>oh</adlib>"], section(), reference=REFERENCE)
    assert rep.lines[0].copied and rep.lines[0].copied_words == ["the sky is bright"]
    assert rep.errors() == ['Line 1 ("the SKY is bright! <adlib>oh</adlib>") '
                            'copies the original lyrics; write a new line.']
    assert not rep.passed() and "originality" not in rep.errors(GATES[:-1])


def test_grams_do_not_span_reference_line_breaks():
    # "light we walk back" crosses the break between two reference lines
    rep = verify_section(["Under the light we walk back"], section(6), reference=REFERENCE)
    assert rep.lines[0].copied is False


def test_unchecked_without_reference():
    rep = verify_section(["The sky is bright"], section())
    assert rep.lines[0].copied is None and rep.gate("originality")
    assert "originality" not in rep.scores()


def test_a_given_hook_is_not_a_copy_but_a_written_one_is():
    sec = section(5, repeats_hook=True)
    args = (["Now we walk back home"], sec)
    kw = dict(hook="We walk back home", reference=REFERENCE)
    assert verify_section(*args, **kw, hook_given=True).lines[0].copied is False
    assert verify_section(*args, **kw).lines[0].copied is True


def test_given_sections_are_not_checked():
    r = Song(RunConfig(["a/one", "b/two"], chorus="original"), ScriptedClient([OWN[1], OWN[2], OWN[3], COPY[4]])).run()
    refrain = r["verification"]["refrain"]
    assert r["parts"]["refrain"]["author"] == "original"
    assert all(l["copied"] is None for l in refrain["lines"]) and "originality" not in refrain["scores"]
    assert r["scores"]["strict_pass"]
    again = rescore(r)
    assert again["verification"] == r["verification"] and again["scores"] == r["scores"]


def test_reference_lines_come_from_the_template():
    assert reference_lines(load_spec("two_voices"))[:2] == ["We watch the light", "We walk back home"]


def old_copying_run(**cfg):
    """A run as scoring version 2 saved it: copying passed the six gates."""
    r = Song(RunConfig(["a/one", "b/two"], gates=list(GATES[:6]), **cfg), ScriptedClient(list(COPY))).run()
    assert r["scores"]["strict_pass"]  # six gates: copying still passed them
    assert r["scores"]["by_singer"]["1"]["adherence"] == 0
    r["scoring_version"] = 2
    for v in r["verification"].values():
        v["gates"].pop("originality")
        v["scores"].pop("originality")
        for l in v["lines"]:
            del l["copied"], l["copied_words"]
    for t in r["turns"]:
        t["final_pass"] = t["first_try_pass"] = True
    return r


def test_rescore_of_an_old_run_adds_the_originality_gate():
    old = old_copying_run(max_retries=0)
    new = rescore(old)
    assert new["scoring_version"] == SCORING_VERSION == 3
    assert new["config"]["gates"] == list(GATES) and old["config"]["gates"] == list(GATES[:6])
    assert not new["scores"]["strict_pass"]
    assert not any(t["final_pass"] for t in new["turns"])
    assert new["scores"]["by_singer"]["1"]["adherence"] == 0
    assert new["verification"]["opening"]["lines"][0]["copied"] is True
    assert rescore(new) == new


def test_rescore_keeps_a_custom_gate_list():
    old = old_copying_run(max_retries=0)
    old["config"]["gates"] = ["syllables"]
    new = rescore(old)
    assert new["config"]["gates"] == ["syllables"] and new["scores"]["strict_pass"]
    assert new["scores"]["by_singer"]["1"]["adherence"] == 0
    assert asdict(load_spec("two_voices")) == new["spec_snapshot"]
