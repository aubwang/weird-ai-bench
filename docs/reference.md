# CLI reference and benchmark details

Start with the [README](../README.md) for setup and a short walkthrough.

## Settings

| Flag | Options | What it does |
|---|---|---|
| `--scenario` | `each_other` (default), `none`, or a YAML path | The framing the singers get: what they're writing and who they address. See [Scenarios](#scenarios) |
| `--names` | `real` (default), `assigned`, `anonymous` | Real model names; personas you pick with one `--persona` per singer (e.g. DeepSeek plays "ChatGPT"); or unnamed singers |
| `--chorus` | `auto` (default), `fixed`, `original`, or a singer number | Auto uses a preset chorus if supplied, otherwise the chorus's first singer writes it. Original uses the song YAML's source chorus |
| `--preset` | bundled ID or YAML path; repeatable | Supplies prewritten sections of any kind, separately from the song template |
| `--track` | `strict` (default), `freeform` | Strict sends failed checks back for a rewrite (up to `--retries`, default 3). Freeform is one shot, and the checks are only scored |
| `--guidance` | `full` (default), `none` | None leaves the song map (syllables, stress, rhyme, pacing notes) out of the prompts: the singers get only the reference lyrics, the line counts, and the output format. Needs `--track freeform`. The checks still score the result |
| `--gates` | any of `structure,syllables,stress,split,rhyme,internal_rhyme,originality` | Which checks must pass on the strict track |
| `--tolerance` | integer | Allowed syllable miss per line (default 0) |
| `--effort`, `--temperature`, `--seed` | | Passed to the model |
| `--max-tokens` | integer | Output token cap per call, including reasoning (default 32000). Reasoning models can use more than 8000 thinking before they answer |

`anonymous` can't be combined with `each_other` (or any scenario with `requires_names`), since the first singer would have nothing specific to answer.

## Scenarios

The system prompt has no built-in framing. The scenario file supplies it, and
weird ai bench adds only mechanics: the cast of singers, the output-format rules, and
the song's reference lyrics. `weird-ai-bench scenarios` lists the bundled ones:
`each_other` (the singers address each other) and `none` (no guidance about who
they address). Keep your own in `scenarios/local/`, which is gitignored.

```yaml
id: third_party
text: >-
  We're writing a parody of "{title}" by {artist}. Every singer is an AI model.
  Both singers are singing to the humans who trained and use them, not to each other.
per_singer:            # optional: extra text for one singer only
  2: You get the last word.
min_singers: 2         # optional limits on the song's singer count
max_singers: 2
requires_names: false  # true rejects --names anonymous
```

`{title}`, `{artist}`, and `{singers}` are filled in from the song. The judge
sees the scenario text too, including per-singer text, but never model names.
Leaderboard comparisons group runs by the scenario's text, not its id or path.

The song YAML is the source of truth for both the original lyrics and pacing.
Put original text in each line's `reference` field; section and speaker tags
are generated from the template. The source is included in both singers'
prompts and saved in run snapshots. It also supplies the originality check: a
generated line fails it, and scores 0, when it repeats a reference line or when
at least 60% of its words sit in 4-word runs taken from the reference. `run --dry-run` previews the prompts without API calls.
The separate text-file options (`--reference-lyrics`, `--original-lyrics`, and
`--chorus-file`) have been removed. `check` still accepts a plain lyric sheet
because it checks that text against the selected YAML spec.

For the original chorus, use `--chorus original` with `reference` on every
chorus line. For a prewritten parody section, use a separate preset:

```yaml
song: two_voices
sections:
  opening:
    - text: The sky is bright
      adlibs: [oh]
  exchange:
    - text: You take the road
    - text: I take the train
```

Select it with `--preset path/to/preset.yaml` on `run` or `matrix`. Section keys
must match the song YAML, and each supplied section must have exactly the
specified number of lines. You can supply a verse, shared chorus, traded
section, ending, or any combination. Multiple `--preset` options can supply
different sections; overlapping sections are rejected. Partial sections are
not supported. The preset's `song` must match the template ID.

Presets are provided as context and are not regenerated or credited to either
model. They still receive verification reports. Leaderboard comparisons keep
different supplied content separate, independent of preset filenames; `--mix`
overrides that grouping. The bundled `two_voices_seed` preset supplies the synthetic
opening section, including an ad-lib. No parody lyrics or preset
selection live in the base song spec.

Ad-libs use `adlibs: [oh]` beside `text` in a preset or beside `reference` in a
song line. Generated lyrics use inline tags such as
`We head home <adlib>home</adlib>`. These marked words are excluded from syllable,
stress, split, end-rhyme, internal-rhyme, hook, and originality checks. Trailing
parentheses such as `(oh)` remain supported. An entire line in parentheses is
a sung aside and is counted; explicit `<adlib>` tags always mark an uncounted
ad-lib. Keep ad-libs on the associated lyric line, not as extra section lines.

The prompts are identical across the two tracks, so any difference between a model's strict and freeform songs comes from the feedback loop alone.

`--guidance none` tests whether a model can hear the song rather than follow a spec. Compare a model's freeform songs with and without guidance: a small gap means it picks up the meter and rhyme scheme from the original lyrics on its own. Unguided runs are one shot, because retry feedback would name the failed checks and give the song map back. They need a template with reference lyrics.

## Check your own lyrics

```sh
weird-ai-bench check mylyrics.txt            # sections marked [opening], [refrain], [exchange], [ending]
weird-ai-bench check - --section opening < opening.txt
weird-ai-bench spec                          # print the song map
```

## Benchmark

```sh
# Every ordered lineup, both tracks, two songs each
weird-ai-bench matrix --models provider/model-a,provider/model-b,provider/model-c \
  --scenarios each_other,none --tracks strict,freeform --samples 2 --out runs/

weird-ai-bench stats runs/                                   # checks only, no judge calls
weird-ai-bench rescore runs/                                 # re-check saved runs after a rules change
weird-ai-bench leaderboard runs/ --judge provider/independent-judge # pairwise judging -> Elo
weird-ai-bench judge runs/*.json --judge provider/independent-judge # rubric scores per song
```

The model IDs above are placeholders; choose available IDs from [OpenRouter](https://openrouter.ai/models) before running them.

`matrix` runs ordered lineups, one model per singer, so each model takes every role, and appends a row per song to `runs/matrix.csv` (per-singer columns are `;`-separated in singer order). `--include-self` lets one model fill several slots. Lineups grow fast with more singers, so `--max-lineups N` samples N of them while keeping each model spread evenly across the singer slots. Use `--dry-run` to list the jobs first. A song costs roughly 5 to 20 calls. With `--seed S`, sample *i* of a configuration gets seed S+*i*, so providers that honor seeds don't repeat a song. If a model's calls fail mid-song (for example, it spends all of `--max-tokens` reasoning), the partial song is still saved with a `failed` note, so failures count against the model instead of disappearing.

`rescore` re-parses and re-checks every saved attempt with the current rules, without calling a model, and rewrites the run files. Retries stay as they happened. `--spec` scores against a revised template of the same shape, such as one with new `slack`. Each run records the scoring rules it was checked under, and `stats` refuses to mix runs from different versions.

`stats` reports, per template, model, track, and guidance: songs, failed songs, line adherence, first-try pass rate per turn, final pass rate, and retries per song. A self-duet counts as one song.

`leaderboard` compares songs written under the same settings, two at a time. Settings include the template, scenario text, reference lyrics, supplied sections, names, chorus, track, guidance, tolerance, temperature, effort, and on the strict track the gates and retries. Pairs are picked so every song is compared about equally often, up to `--max-pairs`, chosen without regard to which pairs are cached or failed. Each pair is judged twice with the order swapped, and a disagreement counts as a tie, which cancels position bias; the output reports how often that happened. A song that failed mid-run loses to every finished song without a judge call.

Results are fitted with a weighted additive Bradley-Terry model: a song's strength is the sum of its singers' model strengths, each weighted by that singer's share of the generated lines as performed. That's what lets a benchmark of shared songs rank individual models, and it credits a repeated chorus to whoever wrote it. The fit puts a normal prior on each strength (`--prior-sd`, default 1 logit, about 170 Elo), so a model that wins every game still gets a finite rating. The 95% intervals come from `--bootstrap` resamples of the songs within each group; treat models with overlapping intervals as tied. Win rate counts only the games where a model's share differed between the two songs. Use at least three models or `--include-self`: with two, A×B and B×A have the same singers and differ only in who wrote which part, so the leaderboard warns that its ranking rests on that alone. Judgments are cached in `judgments.jsonl`, keyed by the judge prompt version, so re-running only pays for new pairs. Next to each model's rating, the table shows its `meter`: the mean automated line adherence over its songs, with unwritten lines counted as 0. It's reported beside the judged ranking, not folded into it.

The judge is blind: it sees "Singer 1", "Singer 2", and so on, never model ids. Model, persona, and family names written into the lyrics ("Claude", "ChatGPT's") are replaced with the matching "Singer N" before judging, or with "a singer" when two singers share a family. The judge also sees the reference lyrics, to judge parody craft, and after each song the automated check results: how many generated lines hit their syllable targets, and which lines missed a count, a rhyme, or copied the original. It's told the checker can mispronounce, so it weighs each miss by how much it would hurt a performance. Assigned character names in the scenario (`--names assigned`) stay visible in the setup, since every song in the group shares them; they're still redacted in the lyrics. Pick a judge from a different family than the singers; weird ai bench warns when it isn't.

Repeat `--judge` to use a panel. Each pair is judged by the panel members that share no family with any singer in either song, and the pair's score is their average. If every member conflicts, the whole panel judges it and the output warns. With judges from three families, every pair of songs has at least one judge outside its families. The output reports how often the judges on a shared pair agreed.

Rubric criteria (1 to 10): singability, humor, parody craft, coherence, and interplay (skipped for solo songs). The judge can't hear the song, so `singability_blended` averages its score with the automated meter score.

## How the checks work

- **Syllables and stress** come from the CMU Pronouncing Dictionary. When a word has several pronunciations ("every," "fire"), any combination that fits counts. Stressed beats must land on a stressed syllable, or on a one-syllable content word. Words like "the," "a," "of," and "and" always fail. Stress and splits are only scored on lines with the right syllable count, so a miscounted line loses points once, for the count.
- **Words dictionaries miss** are handled first: dropped g's ("nothin'"), acronyms sung letter by letter (RL, AGI, D-O-I, GPUs), numbers, hyphenated compounds, and AI names. Anything else is estimated from spelling and listed under "guessed."
- **Rhyme** compares sounds from the last stressed vowel onward. A full rhyme is an exact match. A slant rhyme is the same stressed vowel, or a shared unstressed ending like "-in'." Two-syllable rhymes need both vowels to match. Two sung habits also count as slant. A trailing pronoun can join the word before it ("show me" / "lonely"). An unstressed last syllable can take the rhyme when it's sung hard ("confident" / "tent"). That second one never satisfies a two-syllable rhyme. Slant rhymes score the same as full ones. Two words that sound the same from the start of the stressed syllable ("certain" / "uncertain", "right" / "write") fail the check and score 10%; repeating the same word scores 0.
- **Split lines** (7+5) need a comma or dash exactly at the split.
- **Internal rhyme** needs two words in the line to rhyme, or to share a stressed vowel and the consonant after it ("team / dream").
- Models are asked to write only lyrics inside `<lyrics>` tags. Line numbers, `[10]`-style counts, and bold are stripped anyway, and self-reported counts are never trusted.

Known limits: dictionary stress can't know how a singer will phrase a line, so a correct line occasionally fails a stress check. If one gate is too noisy for your purposes, drop it from `--gates` and it's only scored.

## Adding a song

List bundled templates with `weird-ai-bench songs`. Select one by ID, or pass a YAML path:

```sh
weird-ai-bench spec --spec two_voices
weird-ai-bench run --model provider/model-a --model provider/model-b --spec songs/local/my-song.yaml
```

Copy `weird_ai_bench/data/specs/two_voices.yaml` as a starting point. It demonstrates
the unified format: original source text and pacing constraints live on the same
line entry. For example:

```yaml
opening:
  label: Opening
  singer: 1
  lines:
    - reference: "The sky is bright"
      syllables: 4
      stress: [2, 4]
      note: "Hold the final word."
```

This section sits under the top-level `sections` mapping. The complete file also
needs `id`, `title`, `artist`, `singers` (how many, 1 or more), `generation_order`,
and `performance_order`. `generation_order` includes every section exactly once;
`performance_order` may repeat sections. Section keys and labels are arbitrary.
Each section chooses `singer: N`, `trade: [1, 3, 2, ...]` (one singer per line), or
`sung_by` for the optional shared chorus: `all`, a list such as `[2, 3]`, or `both`
in a two-singer song. Every singer must sing somewhere. The runner supports at
most one shared chorus; repeat its key to perform it again.

Each line takes `syllables`, and optionally `reference`, `stress`, `split`,
`rhyme`, `internal_rhyme`, `hook`, `repeats_hook`, `echo`, `adlibs`, and `note`. Stress
positions count from 1; `split: [7, 5]` specifies a pause after syllable 7.
`hook` can mark any line, not just line one. Rhyme groups are section-local and
take `slant` and `min_syllables`. Pacing annotations must be supplied and checked
by you; the runner does not infer the melody from reference text.

Prewritten parody sections belong in separate presets, never the base song
file. Without a preset chorus, `--chorus auto` asks model 1 to write it.
Templates without a shared chorus still support presets for their other
sections. The pacing and speaker assignments always come from the song YAML.

Embedded source lyrics are rendered into the singer prompts with section and
speaker tags, using the performance order. They also feed the originality
check. Keep local source templates under `songs/local/`, which is gitignored;
the original text is still included in local run snapshots and model requests.

New runs embed the resolved template, so rendering and judging still work after the source YAML is changed or removed. Leaderboard comparisons group runs by the full template, not just its ID.

## Export a chart

Save the pairwise leaderboard, then render it as PNG and SVG:

```sh
uv run weird-ai-bench leaderboard runs/ --judge provider/judge \
  --json-out runs/leaderboard.json
uv run --extra plot python -m weird_ai_bench.chart \
  --input runs/leaderboard.json --out runs/leaderboard-chart
```

The chart uses a 0–100 preference index: the fitted probability of beating a
reference opponent with strength zero (1000 Elo). A score of 50 means equal
strength to that reference. It is relative to the evaluated field, not a
percentage of correct lyrics or a score comparable across different studies.
Intervals transform the leaderboard's bootstrap bounds onto the same scale.
They describe uncertainty conditional on the tested songs. Meter accuracy
remains a separate result from `weird-ai-bench stats`.

To preview the layout without model calls, use `--demo` instead of `--input`.
The preview uses fictional contestants and is visibly labeled synthetic.

## Private files

Keep song source files under `songs/local/`, prewritten material under
`presets/local/`, and your own scenarios under `scenarios/local/`. These directories, raw `lyrics_*.txt` files, local test fixtures,
and generated runs are ignored. Ignoring a file does not remove it from existing
Git history; check what is staged before publishing. Private material is still
sent to the configured model endpoint when you explicitly use it in a run.
