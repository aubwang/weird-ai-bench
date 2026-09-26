# songbench: agent notes

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

Don't put private files under `songbench/data/`, even gitignored ones: hiding
them there means naming them in `.gitignore` or `pyproject.toml`, and those
names are public. Public examples and tests use synthetic text only (the
`two_voices` template). Before committing, check that nothing staged names a
private song: `git diff --cached` and `git grep` over the staged tree.

## Tests

```sh
uv run --extra test pytest            # public tests (tests/)
uv run --extra test pytest tests/local  # private tests, when the local files exist
```

Tests use `ScriptedClient`, so they don't need the network.

## Design decisions

- **Content comes from the models.** Prompts give structure only: no roast
  guidance and no topic hints. The only framing is the scenario file the run
  selects. The runner adds the singer list, the output-format rules, and the
  song's reference lyrics.
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
- **Judging is blind.** The judge sees "Singer 1", "Singer 2", and so on, and
  should come from a different model family than the singers. The leaderboard
  judges each pair twice with the order swapped, and a disagreement counts as a
  tie. The fit is additive Bradley-Terry: a song's strength is the sum of its
  singers' model strengths.
- **Grouping is by content.** Leaderboard groups compare the template,
  scenario text, reference lyrics, and supplied sections by content, never by
  file name or id.

## Open questions

- Is CMUdict stress too noisy to use as a hard gate?
- How many samples per configuration make a ranking stable?
- Should retry feedback name the exact failure, or only the failing line?
