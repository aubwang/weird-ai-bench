"""Drafting templates from lyrics; synthetic lyrics only."""

import pytest
import yaml

from weird_ai_bench.cli import main
from weird_ai_bench.draft import draft
from weird_ai_bench.spec import load_spec, spec_from_dict
from weird_ai_bench.verify import GATES, verify_section

SONG = """\
[Verse 1]
The morning light is breaking
I'm walking down the road, alone
My coffee cup is shaking
The radio is on

[Chorus]
We keep on moving
Nothing's gonna stop us now
We keep on moving (moving on)
We keep on moving on

[Verse 2]
The city noise is waking
I'm humming every song I know
The pavement's hot and baking
And I have far to go

[Chorus]
We keep on moving
Nothing's gonna stop us now
We keep on moving (moving on)
We keep on moving on

[Outro]
Yeah, we keep on moving on
"""


def passes_itself(spec):
    hook = next((l.reference for s in spec.sections.values() for l in s.lines if l.hook), None)
    for sec in spec.sections.values():
        rep = verify_section([l.reference for l in sec.lines], sec, spec.syllable_overrides, hook=hook)
        assert rep.passed(GATES), (sec.key, rep.errors())


def test_sections_chorus_and_order():
    text, spec = draft(SONG, "Moving On")
    assert spec.id == "moving_on" and spec.singers == 1
    assert spec.generation_order == ["chorus", "verse_1", "verse_2", "outro"]
    assert spec.performance_order == ["verse_1", "chorus", "verse_2", "chorus", "outro"]
    assert spec.sections["chorus"].sung_by == [1]
    assert spec.sections["verse_1"].singer == 1
    assert spec_from_dict(yaml.safe_load(text)) == spec
    passes_itself(spec)


def test_line_constraints():
    _, spec = draft(SONG, "Moving On")
    verse = spec.sections["verse_1"].lines
    assert verse[0].syllables == 7 and verse[0].stress == [2, 6]  # MOR-ning, BREAK-ing
    assert verse[1].split == [6, 2]
    assert verse[0].rhyme == verse[2].rhyme == "A" and verse[1].rhyme is None
    chorus = spec.sections["chorus"].lines
    assert chorus[2].reference == "We keep on moving" and chorus[2].adlibs == ["moving on"]
    assert chorus[3].hook and spec.sections["outro"].lines[0].repeats_hook
    # Identical endings rhyme only as a declared refrain.
    assert chorus[0].rhyme == chorus[2].rhyme and chorus[0].refrain == chorus[2].refrain


def test_todos_mark_what_the_text_cant_settle():
    text, _ = draft("We sing it every day\nThe zorbliq is here\n", "Notes")
    assert '# TODO: "every" can be 2 or 3 syllables' in text
    assert '# TODO: "zorbliq" isn\'t in the dictionary' in text
    assert '"us"' not in draft("Nothing's gonna stop us now\n", "Us")[0]


def test_headerless_blocks_become_verses_and_a_chorus():
    lyrics = ("The sky is bright\nThe road is long\n\n"
              "We sing all night\nWe sing our song\n\n"
              "The air is cold\nThe day is done\n\n"
              "We sing all night\nWe sing our song\n")
    _, spec = draft(lyrics, "Blocks")
    assert [spec.sections[k].label for k in spec.generation_order] == ["Chorus", "Verse 1", "Verse 2"]
    assert spec.performance_order == ["verse_1", "chorus", "verse_2", "chorus"]
    passes_itself(spec)


def test_same_sound_endings_are_not_a_rhyme():
    _, spec = draft("[Verse]\nI know I'm right\nI sit and write\n", "Sounds")
    assert all(l.rhyme is None for l in spec.sections["verse"].lines)
    passes_itself(spec)


def test_no_lyrics_is_an_error():
    with pytest.raises(ValueError):
        draft("\n[Verse]\n♪\n", "Empty")


def test_cli_writes_once(tmp_path, capsys):
    lyrics = tmp_path / "night_walk.txt"
    lyrics.write_text(SONG)
    out = tmp_path / "songs" / "night_walk.yaml"
    assert main(["draft", str(lyrics), "--out", str(out)]) == 0
    assert "4 sections, 13 lines" in capsys.readouterr().err
    spec = load_spec(str(out))
    assert spec.title == "Night Walk" and spec.id == "night_walk"
    assert main(["draft", str(lyrics), "--out", str(out)]) == 2
    assert "exists" in capsys.readouterr().err
    assert main(["draft", str(lyrics), "--out", str(out), "--force", "--artist", "Example"]) == 0
    assert load_spec(str(out)).artist == "Example"
    assert main(["draft", str(lyrics)]) == 0
    assert capsys.readouterr().out.startswith("# Draft from")


def test_a_repeated_end_word_apart_is_still_a_refrain():
    _, spec = draft("[Verse]\nWe walk all night\nWe watch the light\nWe sing all night\n", "Night")
    lines = spec.sections["verse"].lines
    assert all(l.rhyme == "A" for l in lines)
    assert lines[0].refrain == lines[2].refrain == "night" and lines[1].refrain is None
    passes_itself(spec)
