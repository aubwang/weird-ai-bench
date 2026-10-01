# Writing song templates and presets

A **song template** defines the requirements and optional original reference.
A **preset** supplies prewritten lyrics for complete sections. Keep your private
files in `songs/local/` and `presets/local/`; use the bundled synthetic templates
as examples.

## Minimal song

```yaml
id: night_walk
title: Night Walk (example)
artist: synthetic example
singers: 1
generation_order: [verse]
performance_order: [verse]
sections:
  verse:
    label: Verse
    singer: 1
    rhymes:
      A: {slant: true}
    lines:
      - {reference: "We take the road", syllables: 4}
      - {reference: "The sky is bright", syllables: 4, stress: [2, 4], rhyme: A}
      - {reference: "We walk back home", syllables: 4}
      - {reference: "We watch the light", syllables: 4, rhyme: A}
```

`singers` fixes how many singers the song has; a run gives one model per singer.
Sections choose `singer: N`, `trade: [1, 2, ...]` for line-by-line exchanges, or
`sung_by` for the chorus: `all`, a list such as `[1]` or `[1, 3]`, or `both`
in a two-singer song. Every singer must sing somewhere. At most one section
can use `sung_by`. Every section appears once in `generation_order`;
`performance_order` can repeat section keys. For a different cast size, write a
separate template.

### Featured artists and backing vocals

A featured artist is a singer who owns one or more sections. They don't need
equal time or a part in the chorus. For a lead and a guest, use `singers: 2`,
assign the lead's sections to `singer: 1`, and the guest verse to `singer: 2`.
Use `sung_by: [1]` if the lead carries the chorus. A duet with a third artist's
guest verse uses `singers: 3` and `singer: 3` for that verse.

Each singer gets a model slot, even for a single section. The guest receives
the sections already written when their turn arrives in `generation_order`.
You can put the same model in every slot to have it write the whole song.

Section labels describe the part: `Chorus`, `Featured Verse`, or
`Outro (backing chorus)`. A choir credit doesn't need its own model slot;
assign its writing to an existing singer. Use `trade` only when you want
separate turns for individual lines. Document any simplified vocal assignments
in the template's notes.

Original reference lines provide context, not required output words. Section
and speaker tags are built automatically. The same reference is used for the
originality report. Leave `reference` out if no reference should be supplied.

## Meter, rhyme, and optional checks

| Field | Meaning |
|---|---|
| `syllables: 8` | Required main-line syllable count |
| `slack: 2` | Syllables either side of the target that still fit, for looser stretches of melody; prompts show the range. `slack: [0, 2]` sets fewer and more separately |
| `stress: [2, 4]` | Required strong beats, counted from 1 |
| `split: [4, 4]` | Pause at the syllable boundary between the two halves |
| `rhyme: A` | End word belongs to group A within this section |
| `internal_rhyme: true` | Two words somewhere within the line must rhyme |
| `internal_rhyme: {word_syllables: 3, end_word: true}` | Two different three-syllable words or acronyms must rhyme on their ending sounds; one must end the line |
| `hook: true` | This line establishes the hook |
| `repeats_hook: true` | This line must end with the established hook |
| `refrain: A` | Lines with the same label intentionally reuse a short phrase or ending; the rest of each line may change |
| `echo: true` | Prompt guidance to echo the hook's last word; not a separate gate |
| `note` | Free-text performance guidance |
| `adlibs: [oh]` | Reference ad-libs, excluded from main-line verification |

In the example, lines 2 and 4 must rhyme **with each other**, not with the
reference words. Rhyme-group names are arbitrary. Omit `rhyme` to leave an ending
unconstrained. Identical ending words do not count as a successful rhyme unless
both lines share a `refrain` label. If those lines also share a rhyme group, the
repeated end word counts as an intentional refrain. The label does not require
the generated lines to copy a phrase from the reference lyrics.

Under `rhymes`, `slant: false` requires full rhyme; `slant: true` permits the
verifier's approximate half-rhyme rules. `min_syllables: 2` requests a
two-syllable rhyme. Slant detection is permissive, including shared unstressed
endings. It cannot establish how convincing a rhyme will sound when sung.
`internal_rhyme: true` checks any eligible word pair, including shared sounds
inside words. The mapping form requires a full rhyme on the words' ending
sounds. Its optional `word_syllables` sets the length of each word, and
`end_word: true` requires one of the pair to end the line. Three-syllable words
can rhyme on just their final syllable; this does not require all three
syllables to rhyme. Uppercase acronyms absent from the dictionary are read
letter by letter. Ad-libs cannot supply the rhyme. Groups do not cross sections.

To keep scoring rhyme but stop using it as a retry condition, run with:

```sh
--gates structure,syllables,stress,split,internal_rhyme,originality
```

Changing the YAML changes the task requirements. Changing `--gates` changes
which failures cause retries. `--track freeform` never retries. `--tolerance 1`
allows a one-syllable count deviation on every line; a line's `slack` applies
instead where it's larger. `weird-ai-bench spec` suggests `slack` where sections of
the same length disagree on counts, since a melody that fits both is looser there. Record these choices when comparing
benchmark results; automatic grouping does not cover every generation setting.

## Prewritten sections

```yaml
song: night_walk
sections:
  verse:
    - text: We take the road
    - text: The sky is bright
      adlibs: [oh]
    - text: We walk back home
    - text: We watch the light
```

Select it with `--preset presets/local/seed.yaml`. Supply any complete section,
including a traded section. The song ID, section names, and line counts must
match the base template. Repeat `--preset` for disjoint sections; overlapping
definitions are errors. Meter and rhyme requirements remain in the song YAML
and are never duplicated in presets.

Supplied sections appear in model context and verification reports. They are
not generated, retried, or credited to the models. Saved runs include their
actual text, so changing or deleting the preset later does not affect rendering.
Leaderboard grouping distinguishes supplied content, independent of file paths.

## Ad-libs

Use `adlibs` beside a source line's `reference` or a preset line's `text`.
Generated responses mark them inline:

```text
<lyrics>
We watch the light <adlib>oh</adlib>
</lyrics>
```

Tagged text does not affect syllables, stress, split locations, end rhyme,
internal rhyme, hook matching, or originality checks. Trailing parenthetical
ad-libs also work. An entire line in parentheses remains a sung aside; explicit
tags always mean an uncounted ad-lib. Keep tags on the main lyric line.

## Preview and run

```sh
weird-ai-bench songs
weird-ai-bench spec --spec songs/local/night_walk.yaml
weird-ai-bench run --model provider/model-a --scenario none \
  --spec songs/local/night_walk.yaml --dry-run
```

Remove `--dry-run` to call the configured endpoint. A preset containing every
section produces verification and saved output without generation calls.
The models do not hear a recording: reference text cannot replace checking the
pacing annotations against the melody yourself.
