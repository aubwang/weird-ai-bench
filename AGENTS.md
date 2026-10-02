# weird ai bench: agent notes

The README covers usage. This file covers how the repo is kept and why it's
shaped the way it is. `CLAUDE.md` is a symlink to this file.

## Private material stays local

This repo is public. Real songs, their lyrics, parody lyrics, and anything that
names them live only in gitignored folders:

- `songs/local/`: song templates with original lyrics
- `presets/local/`: prewritten sections
- `scenarios/local/`: scenario files
- `tests/local/`: tests that use the files above
- `docs/local/`: private notes, including the project's origin and handoff
  (`docs/local/handoff.md`). Read it if it exists.
- `lyrics_*.txt` at the root: raw lyric files

Don't put private files under `weird_ai_bench/data/`, even gitignored ones: hiding
them there means naming them in `.gitignore` or `pyproject.toml`, and those
names are public. Public examples and tests use synthetic text only (the
`two_voices` template). Before committing, check that nothing staged names a
private song outside the results write-up: `git diff --cached` and `git grep` over
the staged tree.

## The published results

The one exception is the results write-up in `README.md`, between the
`<!-- results:start -->` and `<!-- results:end -->` markers, with its charts in
`docs/img/`. weird ai bench is the benchmark's public name. The write-up may
name the real songs and quote lines the models wrote. It never shows the
original lyrics: each parody line links to the moment in the official recording
instead, and lines the originality check flags as close to the original are left
out. Profanity and slurs are starred out.

That section is generated, not hand-edited: `docs/local/build_readme.py
README.md` (the picks and the `readme_results.md` template live in
`docs/local/`). Rebuild it rather than editing it, keep it plain Markdown with
no raw HTML, and keep the original-lyrics rule when changing the generator. The rest of the README is written by hand.

## Tests

```sh
uv run --extra test pytest            # public tests (tests/)
uv run --extra test pytest tests/local  # private tests, when the local files exist
```

Tests use `ScriptedClient`, so they don't need the network.

## Design decisions

- **Content comes from the models.** Prompts give structure only: no roast
  guidance and no topic hints. The only framing is the scenario file the run
  selects. The runner adds the singer list, the output-format rules, the
  song's reference lyrics, and the judge's criteria (melody fit, humor, parody
  craft, coherence, interplay), so writers aren't scored on goals they were
  never told.
- **Songs set their own singer count.** A template has `singers: N`, a run
  gives one model per singer, and one template covers one singer count.
- **Tracks share prompts.** `strict` retries failed checks and `freeform` is
  one shot but still scored, so any difference between them comes from the
  feedback loop.
- **Guidance is its own setting, not a track.** `--guidance none` drops the
  song map from the prompts but keeps the reference lyrics and line counts, so
  it measures whether a model hears the meter instead of following it. It's
  freeform only, since retry feedback would leak the map, and the leaderboard
  never groups guided and unguided songs together.
- **Presets are context, not model output.** They're verified but never
  credited to a model or retried.
- **Copying the original earns nothing.** A generated line made mostly of
  4-grams from the reference lyrics fails the `originality` gate and scores 0,
  since the reference lines pass the meter checks by construction.
- **Judging is blind.** The judge sees "Singer 1", "Singer 2", and so on, and
  model, persona, and family names inside the lyrics are redacted to match. It
  should come from a different model family than the singers. The judge also
  sees the reference lyrics, since it rates parody craft, and the automated
  check results, since a model can't count syllables reliably. The leaderboard
  judges each pair twice with the order swapped, and a disagreement counts as a
  tie. When every family is also a contestant, use a panel of judges from
  several families: each pair skips the judges from its singers' families.
  Meter is reported beside the judged rating, not blended into it.
- **The fit is weighted additive Bradley-Terry.** A song's strength is its
  singers' model strengths weighted by each singer's share of the generated
  lines as performed, so a repeated chorus counts for its writer and a
  self-duet's strength is its model's. It's a MAP fit with a N(0, 1) prior, and
  the intervals come from resampling runs within each group.
- **Failures count.** A song whose API calls failed is saved with what was
  written; it scores 0 on the missing parts and forfeits its leaderboard pairs.
- **Grouping is by content.** Leaderboard groups compare the template,
  scenario text, reference lyrics, and supplied sections by content, never by
  file name or id. Settings that change outcomes (tolerance, temperature,
  effort, and on the strict track, gates and retries) are part of the group.

## Open questions

- Is CMUdict stress too noisy to use as a hard gate?
- How many samples per configuration make a ranking stable?
- Should retry feedback name the exact failure, or only the failing line?
