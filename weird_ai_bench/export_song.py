"""Private, offline render inputs for an explicitly selected saved song.

This module only prepares files. It does not load a singing model, infer timings,
rescore a run, or determine whether its inputs may be used or published.
"""

from __future__ import annotations

import copy
import hashlib
import json
import wave
from pathlib import Path

import yaml

from .spec import spec_from_dict

YING_REPOSITORY = "https://github.com/ASLP-lab/YingMusic-Singer-Plus"
YING_REVISION = "baa409c2e7e5e775f09b4e92a220808f4827d2cc"
YING_MODEL = "ASLP-lab/YingMusic-Singer-Plus"


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text(value, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    if any(c in value for c in "\r\n\x00<>"):
        raise ValueError(f"{name} must be one line without markup")
    return value


def _fields(value, required: set[str], optional: set[str], name: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    missing, unknown = required - value.keys(), value.keys() - required - optional
    if missing or unknown:
        raise ValueError(f"{name}: missing fields {sorted(missing)}, unknown fields {sorted(unknown, key=str)}")
    return value


def performed_lines(run: dict) -> list[dict]:
    """Expand the immutable performance snapshot, never a mutable local template."""
    if (not isinstance(run, dict) or run.get("version") != 2 or
            not isinstance(run.get("spec_snapshot"), dict)):
        raise ValueError("export needs a version 2 run with a spec_snapshot")
    if "failed" in run:
        raise ValueError("cannot export a failed or partial run")
    _text(run.get("id"), "run id")
    if not isinstance(run.get("scores"), dict):
        raise ValueError("run must contain its saved scores")
    try:
        spec = spec_from_dict(run["spec_snapshot"])
    except (KeyError, TypeError, AttributeError) as e:
        raise ValueError(f"invalid run spec_snapshot: {e}") from e
    parts = run.get("parts")
    if not isinstance(parts, dict) or set(parts) != set(spec.sections):
        raise ValueError("run parts must match the snapshot's sections exactly")
    for key, sec in spec.sections.items():
        part = parts[key]
        lines = part.get("lines") if isinstance(part, dict) else None
        if not isinstance(lines, list) or len(lines) != len(sec.lines):
            raise ValueError(f"{key}: saved lyrics must match the section's line count")
        for line in lines:
            _text(line, f"{key} lyric")
            if "|" in line:
                raise ValueError(f"{key}: lyric contains ambiguous Ying phrase delimiter '|'")
    out = []
    for occurrence, key in enumerate(spec.performance_order, 1):
        sec, part = spec.sections[key], parts[key]
        author = part.get("author")
        if isinstance(author, list) and len(author) != len(sec.lines):
            raise ValueError(f"{key}: author list must match the section's line count")
        for index, text in enumerate(part["lines"]):
            singers = (sec.sung_by if sec.is_chorus else
                       [sec.trade[index]] if sec.is_trade else [sec.singer])
            out.append({"performed_line": len(out) + 1, "performance_index": occurrence,
                        "section": key, "section_line": index + 1, "text": text,
                        "sung_by": list(singers),
                        "author": author[index] if isinstance(author, list) else author})
    return out


def _audio(value, base: Path, name: str) -> dict:
    raw = _text(value, name)
    path = Path(raw).expanduser()
    path = (base / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_file():
        raise ValueError(f"{name}: local audio file does not exist: {path}")
    # PCM WAV is deliberately the small, dependency-free export boundary.
    try:
        with path.open("rb") as source:
            with wave.open(source, "rb") as wav:
                channels, sample_width, sample_rate, frames, compression, _ = wav.getparams()
                if (compression != "NONE" or channels not in (1, 2) or
                        sample_rate <= 0 or frames <= 0):
                    raise ValueError(f"{name}: expected nonempty mono/stereo PCM WAV")
                expected = frames * channels * sample_width
                actual = 0
                while chunk := wav.readframes(65536):
                    actual += len(chunk)
                if actual != expected:
                    raise ValueError(f"{name}: truncated WAV data")
    except (wave.Error, EOFError, RuntimeError) as e:
        raise ValueError(f"{name}: expected a readable PCM WAV: {e}") from e
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(),
            "channels": channels, "sample_rate": sample_rate, "frames": frames,
            "sample_width_bytes": sample_width, "duration_seconds": frames / sample_rate}


def _strict_map(raw: str) -> dict:
    """Reject duplicate YAML keys instead of silently replacing a clip or transcript."""
    class UniqueLoader(yaml.SafeLoader):
        pass

    def mapping(loader, node):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node)
            if not isinstance(key, str) or key in result:
                raise ValueError("audio map keys must be unique strings")
            result[key] = loader.construct_object(value_node)
        return result

    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    try:
        return yaml.load(raw, Loader=UniqueLoader)
    except yaml.YAMLError as e:
        raise ValueError(f"invalid audio map YAML: {e}") from e


def prepare_export(run_path: str | Path, audio_map_path: str | Path) -> tuple[dict, list[dict]]:
    """Validate inputs and prepare a provenance manifest and upstream JSONL rows."""
    run_path, audio_map_path = Path(run_path).resolve(), Path(audio_map_path).resolve()
    run_bytes, map_bytes = run_path.read_bytes(), audio_map_path.read_bytes()
    try:
        run = json.loads(run_bytes)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"invalid run JSON: {e}") from e
    lines = performed_lines(run)
    mapping = _fields(_strict_map(map_bytes.decode("utf-8")),
                      {"version", "voice_mode", "clips"}, {"rights_note"}, "audio map")
    if type(mapping["version"]) is not int or mapping["version"] != 1:
        raise ValueError("audio map version must be 1")
    if mapping["voice_mode"] != "single_voice_per_clip":
        raise ValueError("set voice_mode: single_voice_per_clip; automatic duets/choirs are unsupported")
    clips = mapping["clips"]
    if not isinstance(clips, list) or not clips:
        raise ValueError("audio map clips must be a nonempty list")
    rights_note = mapping.get("rights_note")
    if rights_note is not None:
        _text(rights_note, "rights_note")
    next_line, segments, rows = 1, [], []
    for index, clip in enumerate(clips, 1):
        name = f"clip {index}"
        clip = _fields(clip, {"start_line", "end_line", "source_vocal", "source_text"},
                       {"timbre_reference", "timbre_text", "backing"}, name)
        start, end = clip["start_line"], clip["end_line"]
        if (type(start) is not int or type(end) is not int or start != next_line or
                not start <= end <= len(lines)):
            raise ValueError(f"{name}: clips must cover performed lines once, in order; "
                             f"expected start_line {next_line} and end_line <= {len(lines)}")
        source_text = _text(clip["source_text"], f"{name} source_text")
        source = _audio(clip["source_vocal"], audio_map_path.parent, f"{name} source_vocal")
        has_ref, has_text = "timbre_reference" in clip, "timbre_text" in clip
        if has_ref != has_text:
            raise ValueError(f"{name}: timbre_reference and timbre_text must be supplied together")
        timbre = (_audio(clip["timbre_reference"], audio_map_path.parent, f"{name} timbre_reference")
                  if has_ref else copy.deepcopy(source))
        ref_text = (_text(clip["timbre_text"], f"{name} timbre_text") if has_ref else source_text)
        backing = (_audio(clip["backing"], audio_map_path.parent, f"{name} backing")
                   if "backing" in clip else None)
        selected = copy.deepcopy(lines[start - 1:end])
        # IDs never contain a user-provided run id: upstream uses them as filenames.
        identity = json.dumps([_hash(run_bytes), index, start, end, source["sha256"],
                               timbre["sha256"], ref_text], ensure_ascii=False).encode("utf-8")
        item_id = f"song-{_hash(identity)[:16]}-clip-{index:04d}"
        row = {"id": item_id, "melody_ref_path": source["path"],
               "gen_text": "|".join(line["text"] for line in selected),
               "timbre_ref_path": timbre["path"], "timbre_ref_text": ref_text}
        rows.append(row)
        segments.append({"id": item_id, "lines": selected, "source_vocal": source,
                         "source_text": source_text, "timbre_reference": timbre,
                         "timbre_text": ref_text,
                         "timbre_source": "separate_reference" if has_ref else "source_vocal",
                         "backing": backing})
        next_line = end + 1
    if next_line != len(lines) + 1:
        raise ValueError(f"audio map ends at line {next_line - 1}; the performance has {len(lines)} lines")
    snapshot_keys = ("scores", "judge", "verification", "originality", "scoring_version",
                     "generation_scoring_version")
    manifest = {
        "format": "weird-ai-bench-song-export", "version": 1,
        "status": "prepared_only", "selection": "explicit_run_path",
        "run": {"id": run["id"], "path": str(run_path), "sha256": _hash(run_bytes)},
        "audio_map": {"path": str(audio_map_path), "sha256": _hash(map_bytes)},
        "benchmark_snapshot": {k: copy.deepcopy(run[k]) for k in snapshot_keys if k in run},
        "voice_mode": mapping["voice_mode"], "performed_lines": lines, "clips": segments,
        "rights": {"status": "not_verified", "user_supplied_note": rights_note},
        "backend": {"repository": YING_REPOSITORY, "inspected_revision": YING_REVISION,
                    "intended_model": YING_MODEL, "input_file": "ying-input.jsonl",
                    "consumer": "inference_mp.py --input_type jsonl",
                    "model_revision": None, "rendered": False},
        "limits": [
            "Audio metadata and hashes checked; vocal isolation and transcript accuracy not verified.",
            "Each clip is one voice; sung_by records the lyric spec, not generated voice identities.",
            "Line ranges map lyrics to supplied clips, not lyric/audio timings; inspect short clips first.",
            "Backing tracks are provenance only; JSONL does not mix, align, stitch, or render audio.",
            "No checkpoint downloaded or inspected and no model run; no offline-runtime guarantee.",
            "Use a prepared Plus checkpoint explicitly; upstream infer_api.py loads the older model.",
        ],
    }
    # Reject non-finite values, which otherwise create nonstandard JSON artifacts.
    json.dumps(manifest, allow_nan=False)
    return manifest, rows


def export_song(run_path: str | Path, audio_map_path: str | Path, out_dir: str | Path) -> Path:
    """Write a new private output directory; never overwrite inputs or prior exports."""
    out = Path(out_dir).expanduser()
    if out.exists() or out.is_symlink():
        raise ValueError(f"output already exists: {out}; choose a new directory")
    manifest, rows = prepare_export(run_path, audio_map_path)
    payload = "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows)
    manifest["backend"]["input_sha256"] = _hash(payload.encode("utf-8"))
    contents = {".gitignore": "*\n!.gitignore\n",
                "manifest.json": json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                "ying-input.jsonl": payload}
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    for filename, text in contents.items():
        path = out / filename
        with path.open("x", encoding="utf-8") as handle:
            path.chmod(0o600)
            handle.write(text)
    return out / "manifest.json"
