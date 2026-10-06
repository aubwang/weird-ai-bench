# Turn selected lyrics into local singing inputs

`export-song` is an optional production step for a song you want to hear. It
prepares inputs for direct upstream **YingMusic-Singer-Plus** inference. It does
not render audio, change scores, call an LLM, download models, or install anything.
The benchmark's existing dependencies are enough for export.

Pick a saved run explicitly. The `leaderboard` command ranks **writer models**,
not individual songs, so its top model is not automatically a best-song selector.
Read the saved lyric sheets, and, where available, their existing rubric scores
or pairwise judgments. Those can inform a personal shortlist without creating a
new benchmark score or comparing unlike scenarios as if they shared one scale.

## Prepare private inputs

Keep source vocals, backing tracks, transcripts and exports in `runs/` or another
private, gitignored directory. Nothing is uploaded or copied into the export.
Its absolute paths point to the original local audio files. Do not publish the
manifest or JSONL: they contain lyrics, source transcripts, and local paths.

1. Choose a complete version-2 run JSON with its saved `spec_snapshot`.
2. Expand its `performance_order` to number every performed lyric line starting
   at 1. Repeated choruses appear each time they are performed, not just once in
   generation order. The synthetic `two_voices` example has 8 performed lines:
   opening 1; refrain 2–3; exchange 4–5; repeated refrain 6–7; ending 8.
3. Supply clean vocal clips that provide the melody and duration for consecutive
   ranges of those lines. Prepare matching source transcripts yourself. This
   tool does not extract stems, cut clips, or guess alignment from note counts.
4. Write a local YAML audio map. Paths are relative to that YAML file, or absolute.
   Inputs must be nonempty mono/stereo PCM WAV. Only file structure, metadata and
   hashes are checked: the tool cannot verify vocal isolation, transcription,
   alignment, voice identity, or rights.

For example, the following uses synthetic lyrics from `two_voices`. All the WAV
paths are placeholders for clips you supply; no recordings are bundled:

```yaml
version: 1
voice_mode: single_voice_per_clip
# Optional user statement; it never changes the manifest's not_verified status.
rights_note: "Describe the source and permissions, if known."
clips:
  - start_line: 1
    end_line: 1
    source_vocal: opening.wav
    source_text: "The sky is bright"
  - start_line: 2
    end_line: 3
    source_vocal: refrain-first.wav
    source_text: "We watch the light|We walk back home"
    backing: refrain-first-backing.wav
  - start_line: 4
    end_line: 4
    source_vocal: exchange-first.wav
    source_text: "You take the road"
    timbre_reference: chosen-voice.wav
    timbre_text: "The words actually sung in chosen-voice.wav"
  - start_line: 5
    end_line: 5
    source_vocal: exchange-second.wav
    source_text: "I take the train"
  - start_line: 6
    end_line: 7
    source_vocal: refrain-second.wav
    source_text: "We watch the light|We walk back home"
  - start_line: 8
    end_line: 8
    source_vocal: ending.wav
    source_text: "Now we walk back home"
```

Clips must cover all performed lines exactly once, in order, without gaps or
overlaps. One clip may contain several consecutive lines. Each clip renders one
voice: choose clip boundaries and timbre references for singer changes. The
manifest retains the original `sung_by` and writer attribution, but that metadata
does not tell Ying to generate two simultaneous voices. Shared choruses are a
single-voice interpretation in this first export; choir/duet mixing is separate
production work.

A separate timbre reference is optional **for the exporter**. If omitted, the
source vocal is explicitly reused as the timbre reference and `source_text` is
its reference transcript. That aims to retain the source singer's timbre; it does
not imply permission to imitate or publish that voice. If supplied,
`timbre_reference` and its matching `timbre_text` are required together. Original
source words must not be substituted with generated target lyrics in those
reference transcripts.

The generated target lyrics come only from the saved run, in performance order.
Missing/extra lines, failed runs, embedded `|`, multiline lyrics and angle-bracket
markup (including `<adlib>`) are rejected rather than silently dropped or sung as
instructions. Handling overlapping ad-libs requires a separate production plan;
this minimal exporter does not invent one.

## Export

```sh
weird-ai-bench export-song runs/selected-run.json \
  --audio-map runs/local-audio/clips.yaml \
  --out runs/exports/selected-song
```

The destination must not exist. It is created with private permissions and its
own `.gitignore`. An existing export is never overwritten. Repeat with a new
output directory for another explicitly selected run.

- `manifest.json`: run/audio-map hashes, exact copies of saved score and judgment
  fields, performed line order, original singers/writers, audio hashes/metadata,
  source and timbre transcripts, optional backing references, and limitations
- `ying-input.jsonl`: one upstream input row per clip, with exactly `id`,
  `melody_ref_path`, `gen_text`, `timbre_ref_path`, and `timbre_ref_text`

Backing files are recorded only in the manifest. They are not inputs to the
singing model, and this exporter does not mix or stitch them. Generated clip
boundaries and lengths must be checked before any later assembly. Each JSONL
row's `id` is a safe generated filename stem; it does not reuse a run ID as a path.
The manifest says `prepared_only`, records no model-weight revision, and makes no
claim that audio was generated. Saved run bytes and scores remain untouched.

## Direct upstream boundary

The input schema is based on
[`inference_mp.py` at the inspected upstream revision](https://github.com/ASLP-lab/YingMusic-Singer-Plus/blob/baa409c2e7e5e775f09b4e92a220808f4827d2cc/inference_mp.py).
That file reads `--input_type jsonl` and passes the five exported fields to the
model. Its batch path needs an NVIDIA CUDA GPU, even though other upstream entry
points may select a CPU. The exporter does not start this process.

Prepare upstream in a **separate environment**, with a pinned repository revision
and an explicitly selected, locally available **Plus** checkpoint directory.
Keep its large ML dependency tree out of the benchmark installation. Review the
upstream code/model terms, including its Stable Audio component, before use:
[upstream license notes](https://github.com/ASLP-lab/YingMusic-Singer-Plus#-license).
No upstream code or weights are vendored here.

There are important upstream rough edges at that inspected revision:

- The README names `infer.py` and `batch_infer.py`; the repository files are
  `infer_api.py` and `inference_mp.py`
- `infer_api.py` still loads `ASLP-lab/YingMusic-Singer`, the older model.
  `app_local.py` selects `ASLP-lab/YingMusic-Singer-Plus`, but also downloads and
  initializes a separator at startup. Neither is used by this exporter
- The model requires a timbre audio path and its transcript. Its tokenizer and
  model configuration use repository-relative paths, so the separate runtime
  needs the upstream checkout as its working directory
- The batch script catches per-clip errors and can print completion even when a
  clip failed. Existing output filenames are skipped by default. Use a fresh
  render directory, check every expected WAV, and record the actual checkpoint
  revision, settings, seeds and output hashes in your production records
- HF offline settings and local checkpoints alone do not establish that every
  transitive dependency can work offline. Prepare all required assets first and
  test the chosen environment without network access before treating it as an
  offline renderer

A short-clip render and listening test is still needed. This change tests export
and provenance only. It has not established singing quality, English rap/duet
quality, full-song alignment, runtime compatibility, or a working offline model
installation. Successful singing should be kept as a production artifact; it does
not retroactively validate the benchmark's textual melody-fit scores.
