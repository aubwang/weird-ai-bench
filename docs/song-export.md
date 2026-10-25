# Hear a song

`export-song` turns one saved run into inputs for
[YingMusic-Singer-Plus](https://github.com/ASLP-lab/YingMusic-Singer-Plus), which
sings new lyrics to the melody of a vocal clip. weird ai bench only writes the
input files. It doesn't render audio, download models, or change scores, and it
needs nothing beyond the benchmark's own dependencies.

The leaderboard ranks models, not songs, so pick the song yourself from the lyric
sheets under `runs/`.

## Write an audio map

Number the song's lines in performance order, counting a repeated chorus each time
it's sung. The synthetic `two_voices` song has 8: opening 1, refrain 2–3,
exchange 4–5, refrain again 6–7, ending 8.

Then cut clean vocal clips from the original that cover those lines, and write down
what each clip says. The tool doesn't separate stems, cut clips, or align
anything; that's up to you. List the clips in a YAML file:

```yaml
version: 1
voice_mode: single_voice_per_clip
rights_note: "Where the clips came from and whether you can use them."  # optional
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

- Clips cover every line exactly once, in order. A clip can span several lines;
  separate lines in its text with `|`.
- Paths are relative to the YAML file. Every file must be a mono or stereo PCM WAV.
- Each clip is sung by one voice. Ying can't do duets or a group chorus, so split
  clips where the singer changes.
- The voice comes from `timbre_reference` and `timbre_text`, given together, or
  from the source clip itself when they're left out. Transcripts are the words
  actually sung in that audio, not the new lyrics.
- `backing` is recorded in the manifest for your own mixing later; Ying doesn't
  use it.

The new lyrics come from the run. A failed run, or lyrics containing `|`, line
breaks, or tags such as `<adlib>`, are rejected rather than quietly edited.

## Export

```sh
weird-ai-bench export-song runs/selected-run.json \
  --audio-map runs/local-audio/clips.yaml \
  --out runs/exports/selected-song
```

The output directory must not exist yet. It's created readable only by you, with
its own `.gitignore`, and holds:

- `ying-input.jsonl`: one row per clip with `id`, `melody_ref_path`, `gen_text`,
  `timbre_ref_path`, and `timbre_ref_text`, the fields Ying's batch script reads
- `manifest.json`: hashes of the run, the audio map, and every clip; the run's
  saved scores and judgments; who sang and wrote each line; and the rights note

Both files contain lyrics, transcripts, and absolute local paths, so keep them
out of anything you publish.

## Run Ying

The format matches
[`inference_mp.py`](https://github.com/ASLP-lab/YingMusic-Singer-Plus/blob/baa409c2e7e5e775f09b4e92a220808f4827d2cc/inference_mp.py)
at revision `baa409c`, run with `--input_type jsonl`. Install Ying in its own
environment, from its checkout, since its config uses relative paths. Read its
[license notes](https://github.com/ASLP-lab/YingMusic-Singer-Plus#-license) first.
Things to watch at that revision:

- The batch script needs an NVIDIA GPU.
- The README mentions `infer.py` and `batch_infer.py`; the files are
  `infer_api.py` and `inference_mp.py`. `infer_api.py` loads the older
  `YingMusic-Singer` model, so make sure you're running a Plus checkpoint.
- The batch script skips outputs that already exist and can report success when a
  clip failed. Render into an empty directory and check that every WAV is there.

Try a short clip before the whole song.
