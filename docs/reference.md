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

Each singer's conversation keeps only the `<lyrics>` block of its earlier replies, not the working around them; the full reply is saved with each attempt. A reply with no `<lyrics>` tags at all yields no lines. Runs record this as `history: lyrics`; runs saved before the field existed replayed whole replies, and the leaderboard keeps the two apart.

`rescore` re-parses and re-checks every saved attempt with the current rules, without calling a model, and rewrites the run files. Retries stay as they happened. `--spec` scores against a revised template of the same shape, such as one with new `slack` or prosody settings. Each run records the scoring rules it was checked under, and `stats` and `leaderboard` refuse to mix runs from different versions.

Scoring version 6 stops reading a reply with no `<lyrics>` tags as lyrics; rescoring can lower old runs where a model's working was counted as a sung line. Scoring version 4 adds prosody settings, stops crediting a stressed syllable the line is too short to have, and requires the count, stress, and split to pass under one pronunciation. Rescoring can move version 3 scores. A strict run also records `generation_scoring_version`, the rules its retry feedback came from, which rescoring leaves alone; the leaderboard keeps strict runs with different values apart. Runs rescored before this field existed take their scoring version at that point.

`stats` reports, per template, model, track, and guidance: songs, failed songs, line adherence, first-try pass rate per turn, final pass rate, and retries per song. A self-duet counts as one song.

`leaderboard` compares songs written under the same settings, two at a time. Settings include the template, scenario text, reference lyrics, supplied sections, names, chorus, track, guidance, tolerance, temperature, effort, the conversation history form, and on the strict track the gates and retries. Pairs are picked so every song is compared about equally often, up to `--max-pairs`, chosen without regard to which pairs are cached or failed. Each pair is judged twice with the order swapped, which cancels position bias. A song's score for the pair averages the two orders, except that opposite wins (the verdict flipped with the order) count as a tie: a win in both orders is 1, a win and a tie 0.75, a flip 0.5. Scores come from the saved votes, so cached judgments follow this rule without new calls. The output reports how often the verdict changed with the order. A song whose model failed mid-run (a refusal, every token spent before answering, empty replies) loses to every finished song without a judge call. A song the provider failed (overload, 5xx, rate limits that outlast the retries, network errors, an unavailable model) is saved with `failed.kind: provider` and left out of `leaderboard` and `stats` with a warning naming it, so rerunning it fills the gap; the JSON lists them under `provider_failures`. Runs saved before the kind was recorded count against the model unless their error text is a recognisable service error.

Results are fitted with a weighted additive Bradley-Terry model: a song's strength is the sum of its singers' model strengths, each weighted by that singer's share of the generated lines as performed. That's what lets a benchmark of shared songs rank individual models, and it credits a repeated chorus to whoever wrote it. The fit puts a normal prior on each strength (`--prior-sd`, default 1 logit, about 170 Elo), so a model that wins every game still gets a finite rating. The 95% intervals come from `--bootstrap` resamples of the songs within each group; treat models with overlapping intervals as tied. A model's interval uses only the resamples that include at least one of its compared songs. With one song per model per group, a resample often leaves a model out, and counting those draws would pin its interval to the prior's mean. Win rate counts only the games where a model's share differed between the two songs. Use at least three models or `--include-self`: with two, A×B and B×A have the same singers and differ only in who wrote which part, so the leaderboard warns that its ranking rests on that alone. Judgments are cached in `judgments.jsonl`, keyed by the judge, the judge prompt version, and a hash of everything the judge sees for each song, so re-running only pays for new pairs, and a rescored run is judged again. Version 5 shows the judge stress, pause, and guessed-pronunciation misses, so cached version 4 judgments aren't reused. Next to each model's rating, the table shows `adher` (composite adherence), `syll` (count-pass including declared slack/tolerance), and `copy` (the share of checked lines copied from the original, which `syll` doesn't penalize). These diagnostics are not folded into the judged ranking. The JSON includes the individual component metrics defined below.

The judge is blind: it sees "Singer 1", "Singer 2", and so on, never model ids. Model, persona, and family names written into the lyrics ("Claude", "ChatGPT's") are replaced with the matching "Singer N" before judging, or with "a singer" when two singers share a family. In a pairwise comparison, company and product names of any family in either song ("Google", "ChatGPT") become `[AI name]` in both songs, and the other song's exact model names do too, so a name reads the same on both sides and can't hint at who wrote which song; personas and the song's own model names still become "Singer N". The cache key covers this, so only pairs whose text changes are judged again. The judge also sees the reference lyrics, to judge parody craft, and after each song the automated check results: how many generated lines hit their syllable targets, and which lines missed a count, a stress, a pause, or a rhyme, relied on guessed pronunciations, or copied the original. It's told the checker can mispronounce, so it weighs each miss by how much it would hurt a performance. Assigned character names in the scenario (`--names assigned`) stay visible in the setup, since every song in the group shares them; they're still redacted in the lyrics. Model and family names the scenario itself mentions stay visible in both the setup and the lyrics, so the setup reads the same whichever models wrote the song. Pick a judge from a different family than the singers; weird ai bench warns when it isn't.

Repeat `--judge` to use a panel. Each pair is judged by the panel members that share no family with any singer in either song, and the pair's score is their average. If every member conflicts, the whole panel judges it and the output warns. With judges from three families, every pair of songs has at least one judge outside its families. The output reports how often the judges on a shared pair agreed. `--max-judges-per-pair N` caps each pair at N of its eligible judges, to save cost. The pick is a hash of the two run ids and the judge's name, so it doesn't change when the schedule grows or reruns, and cached verdicts stay usable; across many pairs each judge gets about an equal share. With a cap of 1 there's no panel agreement to report.

To grow a ranking in stages, pass `--schedule FILE`. Pairs already in the file stay in the schedule, new pairs are picked the usual balanced way until there are `--max-pairs` in total (counting the kept ones), and the schedule is saved back. Adding songs, samples or scenarios later then only pays for the new pairs, since the kept pairs' verdicts are cached. Raising `--max-judges-per-pair` later keeps each pair's earlier judges too, because the pick for N+1 judges includes the pick for N.

Pairwise judge version 8 accepts only JSON integers `1`, `2`, or the string `"tie"` (case-insensitive) as verdicts. Missing or invalid verdicts, malformed replies, and model API failures leave that judge's pair unresolved. They never become ties or enter the rating fit. Other resolved panel votes still count; pairs without any resolved vote are skipped. The CLI and JSON report scheduled and skipped pairs, unresolved judge-pair judgments, and each judge's resolved count, explicit ties (both orders voted tie), and order flips. Flips still count as ties in the fit but are separate from explicit ties in the per-judge summary. Flip rates and panel agreement use resolved judgments only.

Prompt caching: requests to Anthropic models carry cache breakpoints on the system prompt, the conversation so far, and the setup every pair in a judging group shares; other providers cache repeated prefixes on their own, and their prompts are sent unchanged. Caching changes billing, not the text a model reads. The leaderboard judges each group's pairs together so the shared setup stays cached; judgments are independent, so the order changes nothing else.

`preflight MODEL...` makes one small call per model before a paid run and reports whether it answered, its reasoning tokens, latency and cost. With `--effort`, it flags models that report zero reasoning tokens at that setting, since nominally equal efforts can differ between providers. A provider that doesn't report reasoning tokens shows `?` and a note, not a failure, since preflight can't tell either way. `--long` also sends one judge-sized prompt, to catch size-dependent rate limits; the cost column includes it. A cost ending in `+` is a floor: some call didn't report its cost. It exits nonzero when any model has a problem.

Rate limits (HTTP 429, or an error body with code 429) are retried with waits that double from 5 seconds up to a minute, up to 8 times, honoring a `Retry-After` header given in seconds. Other transient errors get 4 short retries. Errors that would repeat, such as a bad request or an empty refusal (`finish_reason=content_filter`), fail at once. An API error that survives those retries stops further calls to that judge for the current invocation, including the other order if it has not been attempted. The failed pair is unresolved; later judge-pairs without resolved cache entries are reported as unattempted. Other judges and resolved cache entries continue normally. Inspect the saved error and fix credentials, settings, or availability before retrying. Malformed verdicts do not disable the judge. Per-judge `scheduled` counts include unresolved, unattempted, and (in cached-only mode) `missing_cached` judgments, but exclude forfeit pairs and pairs that exclude that judge's family.

Each record saves both presentation orders, raw response text, explanations, available usage and cost data, and errors. Unresolved records remain in the append-only cache for inspection; a normal rerun retries both orders of those judgments. Resolved judgments are reused. Older judge versions are not reused because they may have silently treated invalid responses as ties. Saved responses can contain private song text, so keep judgment caches and JSON exports local alongside the runs.

The JSON `records` array now includes unresolved judgments from skipped pairs: their `winner`, `score_a`, and `consistent` fields are null. Consumers that calculate scores must exclude records with `status == "unresolved"`; forfeit records remain valid. Per-order `attempted` distinguishes an API failure from an order skipped after a failure, and unavailable response fields are null. Version 8 does not migrate older caches: the next normal run pays for fresh judgments even where an older verdict was valid.

`new_judging_cost` reports known costs and calls without cost data for this invocation only, excluding cached judgments. Failed calls have unknown cost, not an assumed zero bill. Historical attempts, including superseded unresolved judgments, remain in `judgments.jsonl`; current report records contain the latest selected judgment for each scheduled judge-pair.

Rubric criteria (1 to 10): singability, humor, parody craft, coherence, and interplay (skipped for solo songs). The judge can't hear the song, so `singability_blended` averages its score with the automated meter score.

## How the checks work

- **Syllables and stress** come from the CMU Pronouncing Dictionary. When a word has several pronunciations ("every," "fire"), one combination must fit the count, stress, and split together. Each required stress must land on a stressed syllable, or on a one-syllable content word. Words like "the," "a," "of," and "and" always fail. Stress and splits are only scored on lines with the right syllable count, so a miscounted line loses points once, for the count.
- **Words dictionaries miss** are handled first: dropped g's ("nothin'"), acronyms sung letter by letter (RL, AGI, D-O-I, GPUs), numbers, hyphenated compounds, and AI names. Anything else is estimated from spelling and listed under "guessed."
- **Rhyme** compares sounds from the last stressed vowel onward. A full rhyme is an exact match. A slant rhyme is the same stressed vowel, or a shared unstressed ending like "-in'." Two-syllable rhymes need both vowels to match. Two sung habits also count as slant. A trailing pronoun can join the word before it ("show me" / "lonely"). An unstressed last syllable can take the rhyme when it's sung hard ("confident" / "tent"). That second one never satisfies a two-syllable rhyme. Slant rhymes score the same as full ones. Two words that sound the same from the start of the stressed syllable ("certain" / "uncertain", "right" / "write") fail the check and score 10%; repeating the same word scores 0.
- **Prosody settings** list the ways a line can be sung, each with its own count, stress, and split; a syllable held over several notes counts once. A line must fit one setting completely. See the [authoring guide](authoring.md#prosody-settings-and-melisma).
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

Copy `weird_ai_bench/data/specs/two_voices.yaml` as a starting point, or draft one from
a lyrics file with `weird-ai-bench draft lyrics.txt --out songs/local/my-song.yaml`
(see the [authoring guide](authoring.md#start-from-a-draft)). The example demonstrates
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
positions count from 1; `split: [7, 5]` specifies a pause after syllable 7. A line that can be sung more than one way takes `prosody` settings instead of `syllables`, `stress`, `split`, and `slack`; see the authoring guide.
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


## Component metrics (diagnostics version 1)

New and rescored runs add `scores.by_singer.<singer>.metrics`. Existing scorer
version 4 rules, retry gates, composite adherence and judged rankings are
unchanged. The additive diagnostics carry their own `version: 1`.

Each rate contains `passed`, `total` and `rate` (null when nothing is annotated):

- `exact_syllables`: some pronunciation matches an authored count exactly,
  ignoring legacy slack/tolerance. Explicit melisma alternatives are allowed;
  this does not require that the exact-count reading also passes stress.
- `syllables`: count passes the declared settings, including legacy slack/tolerance.
- `stress` and `phrase`: count plus the named constraint passes under at least
  one allowed setting. Denominators include only lines with that constraint in
  any authored setting. An unconstrained alternative can satisfy it. These
  diagnostics are independent; the existing scorer still requires a coherent
  reading when applying combined retry gates.
- `rhyme`: the existing rhyme rule passes, for lines in authored groups of at
  least two members (excluding hook repeats). A missing rhyme partner does not
  remove the written member from the denominator. No rhyme weights change.

Per-singer denominators count expected generated line slots, once per generated
section, not repeated performances. Missing or blank lines fail applicable
checks. Presets and original supplied sections are excluded. Unannotated
constraints are null rather than perfect. Extra lines remain structure failures;
these metrics assess the expected slots, not structural completeness.

`missing`, `copy_checked`, `copied` and `guessed_pronunciation` are counts.
Copy checking counts only nonblank observed lines actually checked against a
reference. Missing lines are not verified original. Fit diagnostics are raw:
a copied line may fit perfectly, but still earns zero composite adherence.
The leaderboard reports `copy_rate` (`copied` over `copy_checked`) beside them.
Estimated pronunciations can pass existing checks, so their count stays visible;
this is not proof of pronunciation or singability. These synthetic regression
fixtures are not a substitute for human calibration.

Leaderboard JSON pools component numerators/denominators across singer-runs and
reports `available_singer_runs` and `missing_singer_runs` per model. Any legacy
or incompatible diagnostics make that model's component rates null rather than
silently reporting a partial subset. Rescore preserved copies to populate them;
no new generation is needed. Composite adherence retains its existing mean of
singer-run means. Neither statistic is a confidence interval.

For compatibility, leaderboard JSON retains `meter` as a **deprecated alias for
composite adherence**, adds the correctly named `adherence`, and declares
`meter_deprecated_alias: "adherence"`. `meter_by_model()` likewise remains a
legacy alias for `adherence_by_model()`. New clients should use `adherence` or
`metrics`, not infer syllable accuracy from `meter`. The CLI no longer uses the
misleading label. Existing published results are not regenerated by this change.
