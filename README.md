# songbench

Two LLMs co-write a parody duet against a song template. songbench relays their turns, checks syllables, stress, and rhyme, and optionally judges the finished song. Use it to compare constraint-following, humor, and how well one singer responds to the other.

The bundled default, `two_voices`, is a small synthetic example, not a transcription of a recording. Each song has its own YAML template. Original lyrics and private parody material belong in ignored local files; the public examples and tests use synthetic text. See [the authoring guide](docs/authoring.md) for pacing, rhyme groups, presets, and ad-libs.

## Install

```sh
pip install -e .            # or: pip install -e '.[test]' to run the tests
export OPENROUTER_API_KEY=...
```

Python 3.10+. Every model is an [OpenRouter](https://openrouter.ai/models) id. To use any other OpenAI-compatible endpoint instead, set `SONGBENCH_BASE_URL` (for example `http://localhost:11434/v1`) and `SONGBENCH_API_KEY`.

When `SONGBENCH_BASE_URL` is set, the client requires `SONGBENCH_API_KEY` (or an explicit key passed to the Python client); it never falls back to `OPENROUTER_API_KEY`.

## Write one song

```sh
songbench run --model-1 openai/gpt-5.1 --model-2 anthropic/claude-sonnet-5 --spec two_voices --preset two_voices_seed
```

This prints the lyric sheet and saves `runs/<id>.json` (every prompt, response, check, and retry) and `runs/<id>.md`. Add `--dry-run` to print the prompts without calling anything, and `--judge <model>` to score the song when it's done.

Completed songs are saved before judging, so a judge failure preserves the generation. Retry judging later with `songbench judge runs/<id>.json --judge <model>`.

The turn order follows the selected spec. The example has a refrain, an opening, a traded section, and an ending. Other templates can use different sections, orders, and trading patterns, including no shared chorus. Each model has its own conversation thread and sees the other singer's final lines, never their failed drafts.

## Settings

| Flag | Options | What it does |
|---|---|---|
| `--mode` | `each_other` (default), `third_party`, `none` | Who the singers address: each other, the humans who trained and use them, or no guidance |
| `--names` | `real` (default), `assigned`, `anonymous` | Real model names; personas you pick with `--persona-1/-2` (e.g. DeepSeek plays "ChatGPT"); or "two unnamed AI models" |
| `--chorus` | `auto` (default), `fixed`, `original`, `model_1`, `model_2` | Auto uses a preset chorus if supplied, otherwise model 1 writes it. Original uses the song YAML's source chorus |
| `--preset` | bundled ID or YAML path; repeatable | Supplies prewritten sections of any kind, separately from the song template |
| `--track` | `strict` (default), `freeform` | Strict sends failed checks back for a rewrite (up to `--retries`, default 3). Freeform is one shot, and the checks are only scored |
| `--gates` | any of `structure,syllables,stress,split,rhyme,internal_rhyme` | Which checks must pass on the strict track |
| `--tolerance` | integer | Allowed syllable miss per line (default 0) |
| `--effort`, `--temperature`, `--seed`, `--max-tokens` | | Passed to the model |

`anonymous` can't be combined with `each_other`, since the first singer would have nothing specific to answer.

The song YAML is the source of truth for both the original lyrics and pacing.
Put original text in each line's `reference` field; section and speaker tags
are generated from the template. The source is included in both singers'
prompts and saved in run snapshots. It also supplies the automatic 4-gram
originality check. `run --dry-run` previews the prompts without API calls.
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

## Check your own lyrics

```sh
songbench check mylyrics.txt            # sections marked [opening], [refrain], [exchange], [ending]
songbench check - --section opening < opening.txt
songbench spec                          # print the song map
```

## Benchmark

```sh
# Every ordered pair, both tracks, two songs each
songbench matrix --models openai/gpt-5.1,anthropic/claude-sonnet-5,deepseek/deepseek-v4 \
  --modes each_other,third_party --tracks strict,freeform --samples 2 --out runs/

songbench stats runs/                                   # checks only, no judge calls
songbench leaderboard runs/ --judge google/gemini-3-pro # pairwise judging -> Elo
songbench judge runs/*.json --judge google/gemini-3-pro # rubric scores per song
```

The model ids above are examples; check [openrouter.ai/models](https://openrouter.ai/models) for current ones.

`matrix` runs ordered pairs, so each model takes both roles, and appends a row per song to `runs/matrix.csv`. Use `--dry-run` to list the jobs first. A song costs roughly 5 to 20 calls.

`stats` reports, per model and track: line adherence, first-try pass rate per turn, final pass rate, and retries per song.

`leaderboard` compares songs written under the same settings, two at a time. Each pair is judged twice with the order swapped, and a disagreement counts as a tie, which cancels position bias. Results are fitted with an additive Bradley-Terry model: a song's strength is the sum of its two models' strengths, which is what lets a duet benchmark rank individual models. Judgments are cached in `judgments.jsonl`, so re-running only pays for new pairs.

The judge is blind: it sees "Singer 1" and "Singer 2", never model ids. Persona names inside the lyrics are still visible with `--names real` or `assigned`. Pick a judge from a different family than the singers; songbench warns when it isn't.

Rubric criteria (1 to 10): singability, humor, parody craft, coherence, and interplay. The judge can't hear the song, so `singability_blended` averages its score with the automated meter score.

## How the checks work

- **Syllables and stress** come from the CMU Pronouncing Dictionary. When a word has several pronunciations ("every," "fire"), any combination that fits counts. Stressed beats must land on a stressed syllable, or on a one-syllable content word. Words like "the," "a," "of," and "and" always fail.
- **Words dictionaries miss** are handled first: dropped g's ("nothin'"), acronyms sung letter by letter (RL, AGI, D-O-I, GPUs), numbers, hyphenated compounds, and AI names. Anything else is estimated from spelling and listed under "guessed."
- **Rhyme** compares sounds from the last stressed vowel onward. A full rhyme is an exact match. A slant rhyme is the same stressed vowel, or a shared unstressed ending like "-in'." Two-syllable rhymes need both vowels to match.
- **Split lines** (7+5) need a comma or dash exactly at the split.
- **Internal rhyme** needs two words in the line to rhyme, or to share a stressed vowel and the consonant after it ("team / dream").
- Models are asked to write only lyrics inside `<lyrics>` tags. Line numbers, `[10]`-style counts, and bold are stripped anyway, and self-reported counts are never trusted.

Known limits: dictionary stress can't know how a singer will phrase a line, so a correct line occasionally fails a stress check. If one gate is too noisy for your purposes, drop it from `--gates` and it's only scored.

## Adding a song

List bundled templates with `songbench songs`. Select one by ID, or pass a YAML path:

```sh
songbench spec --spec two_voices
songbench run --model-1 provider/model-a --model-2 provider/model-b --spec songs/local/my-song.yaml
```

Copy `songbench/data/specs/two_voices.yaml` as a starting point. It demonstrates
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
needs `id`, `title`, `artist`, `generation_order`, and `performance_order`.
`generation_order` includes every section exactly once; `performance_order` may
repeat sections. Section keys and labels are arbitrary. Each section chooses
`singer: 1` or `2`, `trade: [1, 2, ...]` (one singer per line), or `sung_by: both`
for the optional shared chorus. The runner currently supports two singers and
at most one shared chorus; repeat its key to perform it again.

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

## Private files

Keep song source files under `songs/local/` and prewritten material under
`presets/local/`. Both directories, raw `lyrics_*.txt` files, local test fixtures,
and generated runs are ignored. Ignoring a file does not remove it from existing
Git history; check what is staged before publishing. Private material is still
sent to the configured model endpoint when you explicitly use it in a run.

## Tests

```sh
pytest
```

The verifier tests use lines that were checked by hand, and the run tests drive complete songs through a scripted client, so no network is needed.
