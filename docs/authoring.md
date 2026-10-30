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

## Start from a draft

`weird-ai-bench draft` writes a first version of a template from a lyrics file:

```sh
weird-ai-bench draft lyrics_my-song.txt --out songs/local/my-song.yaml --artist "Someone"
```

Mark sections with `[Verse 1]`, `[Chorus]`, and so on, or separate them with blank
lines. A section whose words come back later is sung again rather than copied, and
the most repeated one becomes the chorus. Trailing `(...)` text becomes ad-libs.

From the words alone, the draft fills in syllable counts, rhyme groups, a `split`
where a line has one comma or dash, and `hook` and `repeats_hook` when other lines
end with a chorus line. Lines with the same end word share a `refrain` label.
Stresses are marked only on the stressed syllable of longer words, where the
dictionary leaves no doubt. Before writing, it checks the original lyrics against
the draft and drops anything they'd fail, so the source always passes.

The draft is for one singer. For a duet, raise `singers` and assign the sections.
`# TODO` comments mark words the dictionary doesn't know or can count two ways.
Then listen through: a held note, a squeezed syllable, or a stress the melody moves
needs your edit, and `weird-ai-bench spec --spec songs/local/my-song.yaml` shows
the result.

## Meter, rhyme, and optional checks

| Field | Meaning |
|---|---|
| `syllables: 8` | Required main-line syllable count |
| `slack: 2` | Syllables either side of the target that still fit, for looser stretches of melody; prompts show the range. `slack: [0, 2]` sets fewer and more separately |
| `stress: [2, 4]` | Syllables that must be stressed, counted from 1 (syllables, not notes) |
| `split: [4, 4]` | Pause at the syllable boundary between the two halves |
| `split_mode: word` | Require a word boundary at `split`, with punctuation optional; the default `punctuation` retains the original comma/dash rule |
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
instead where it's larger. Neither says where the extra syllable goes or moves the
stresses; for that, use prosody settings. `weird-ai-bench spec` suggests `slack`
where sections of the same length disagree on counts, since a melody that fits
both is looser there. Record these choices when comparing benchmark results;
automatic grouping does not cover every generation setting.

## Prosody settings and melisma

When a line can be sung more than one way, list each way as a setting instead of
giving the line `syllables`, `stress`, `split`, and `slack`:

```yaml
- reference: "The sky, is bright"
  prosody:
    - name: four-attacks
      note_spans: [1, 1, 1, 1]
      stress: [2, 4]
      split: [2, 2]
    - name: held-ending
      note_spans: [1, 1, 2]
      stress: [2, 3]
      split: [2, 1]
```

`note_spans` gives the number of notes each syllable takes. Both settings cover
the same four notes: `four-attacks` puts a syllable on each, and `held-ending`
holds the last syllable over two notes (melisma). A setting's syllable count is
the length of `note_spans`, so this line takes four syllables or three, never
anything else. Every setting for a line must cover the same number of notes, and
names must be unique within the line.

`stress` and `split` count the setting's own syllables. A line passes when it
fits one setting completely, under one pronunciation: it can't take its count from
one setting and its stresses from another. The checker reports the closest
setting. Templates with settings can't use `--tolerance`, and lines with and
without settings can share a template.

On the strict track, the enabled meter gates must all pass under one setting and
pronunciation, so turning off the stress gate never causes a split retry. Scores
use the best reading across all three meter checks, whatever the gates.
`meter_joint_pass` in a section's report says whether one reading passed all three.

Settings are your annotation, checked against the recording or score; the checker
can't hear the song. Optional timing maps below can describe rests and pickups.
The settings still cannot express two syllables squeezed onto one original note
without changing their common note-count convention. To try the example without an API key:

```sh
weird-ai-bench check examples/melisma.txt --spec examples/melisma.yaml
```

## Optional rhythm guidance

Timing is opt-in prompt context, not an audio-performance score. See
[`examples/rhythm.yaml`](../examples/rhythm.yaml) for a complete synthetic example.
Add `rhythm` inside a prosody setting:

```yaml
reference: We walk back home
prosody:
  - name: breath-after-two
    note_spans: [1, 1, 1, 1]
    stress: [2, 4]
    split: [2, 2]
    split_mode: word
    rhythm:
      tempo_bpm: 112
      beats_per_bar: 4
      start_beat: 0
      onsets: [0, 0.5, 2.5, 3]
      durations: [[0.5], [1.5], [0.5], [1]]
      reference_syllables: [We, walk, back, home]
```

All times use quarter-note beats. `onsets` are relative to the first syllable,
starting at zero; `start_beat` gives that syllable's zero-based position within
the bar, so pickups retain their phase. `tempo_bpm` is the quarter-note tempo.
Each nested duration list describes the distinct note attacks on one syllable.
Combine tied note segments into one duration; keep a melisma's separate attacks
in one list. The lengths of these lists must equal `note_spans`. A positive gap
before the next syllable is a rest. Notes within a syllable are contiguous.
Changing tempos or meter within a line is not supported by this representation.

Choose a writer prompt format with `--rhythm`:

- `none` (default): existing count/stress/rhyme map; omit the timing.
- `beats`: exact syllable onsets, note durations, bar position and tempo.
- `grid`: the same timing as compact symbols, with an explicit legend. `q`,
  `s`, `M`, `L`, `H` mean 0.25, 0.5, 1, 1.5 and 2 beats; other lengths stay
  numeric. `+` connects note attacks on one syllable, `|Nb|` is an N-beat rest,
  and `>` marks an offbeat start held across a whole-beat boundary. It does not
  automatically add a stress requirement.
- `aligned`: exact beats plus the source syllable labels, indexed by position.
  The source is still context, not words the model must reuse.

Every setting needs timing for a timing-enabled run; `aligned` also needs
source syllable labels for every setting. Timing cannot be combined with
`--guidance none`. Preview without model calls:

```sh
weird-ai-bench spec --spec examples/rhythm.yaml --rhythm grid
weird-ai-bench run --model provider/model --scenario none \
  --spec examples/rhythm.yaml --rhythm beats --track freeform --dry-run
```

The four writer formats keep the same scoring rules and accepted settings.
Their saved configs, leaderboard groups and stats remain separate. For templates
with timing, judges always receive the exact beat map, independently of which
format the writer received. This holds judge information constant across a
prompt experiment; it does not validate a text judge as a listening evaluator.

`split_mode: word` checks that a word ends at the specified syllable boundary
under the same pronunciation used for count and stress. A comma is optional.
The default remains `punctuation` for existing templates and snapshots. Within
prosody settings, put `split_mode` beside that setting's `split`; for ordinary
lines, put it beside the line's `split`.

Other timed rests get a `rest_boundary_ok` diagnostic. It asks whether one
equally scoring pronunciation can put word boundaries at all those rests. It
does not affect retries, numeric scores or judge check notes. Neither timing
nor long notes automatically create new hard stress rules or accepted syllable
counts. Review those choices by singing candidate lines before adopting them.

Scoring version 5 adds the explicit word-boundary mode; legacy punctuation
templates retain their behavior. Judge version 6 supports timing context.
Existing saved runs are not rewritten. Use `rescore` before combining scoring
versions, and keep timing experiments separate from published rankings until
their checks have been calibrated against listening judgments.

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
# Soft parody-craft guidance

A section may include `craft_notes`, a list of nonempty strings describing
recognizable devices in the source: a rhetorical turn, a returning hook, a
contrast, or a memorable sound pattern. Use source structure only; do not supply
new topics, jokes, or model answers. For example, synthetic material may use:

```yaml
craft_notes:
  - The opening establishes a scene and the ending returns to a destination; transform that movement without retaining the source words.
```

With full guidance, writers and judges receive the same notes. A template with
notes also opts into expanded qualitative criteria for parody craft and
coherence: recognizable transformations matter, and a consistent comic argument
can hold a song together without a continuous story. Exact wording and every
listed device are not required, but enough other recognizable features must
remain for the lyrics to work as a transformation of the source. Funny lyrics
that merely fit the same melody can earn humor credit while earning little
parody-craft credit. These notes do not add automated internal-rhyme
checks, copying exceptions, or other hard gates. Existing musical constraints
still apply.

With `guidance=none`, both the notes and expanded criteria are omitted from
writers and judges; the legacy qualitative criteria apply. Templates without
notes retain their earlier prompt criteria. Notes are saved in template
snapshots, affect content grouping, and enter judge-input cache hashes. Judge
version is 7; automated scoring remains version 5. Preserve prior runs and
ratings instead of silently replacing their snapshots or expectations. An
exploratory rejudgment under changed expectations must be labelled as such; a
fresh run is needed to measure responses to the new writer guidance.

Version 7 invalidates version-6 cached judgments, including legacy pairs whose
prompt text is unchanged. Merely opening saved reports makes no calls, but a
future live `leaderboard` invocation can pay to rejudge those pairs. Keep old
reports/caches intact. Craft pairwise prompts include the full criterion
definitions in both orders, and those definitions enter the craft input hash.
For explicitly mixed comparisons, each song retains its own stated criteria.

Author calibration examples separately from writer inputs. A short callback
is not automatically copied text, but the current copying heuristic can still
flag heavily overlapping lines. Audit examples before changing its threshold;
`craft_notes` never whitelist phrases.
