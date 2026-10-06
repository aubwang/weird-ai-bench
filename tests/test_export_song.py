"""Synthetic render-input contracts; no ML runtime or actual singing is exercised."""

import copy
import hashlib
import json
import socket
import struct
import subprocess
import wave

import pytest
import yaml

from weird_ai_bench.cli import main
from weird_ai_bench.export_song import export_song, performed_lines, prepare_export
from weird_ai_bench.llm import ScriptedClient
from weird_ai_bench.orchestrate import RunConfig, Song


@pytest.fixture
def inputs(tmp_path):
    client = ScriptedClient(["<lyrics>We watch the light\nWe walk back home</lyrics>",
                             "<lyrics>The sky is bright</lyrics>", "<lyrics>You take the road</lyrics>",
                             "<lyrics>I take the train</lyrics>", "<lyrics>Now we walk back home</lyrics>"])
    run = Song(RunConfig(["a/x", "b/y"], track="freeform"), client).run()
    run["judge"] = {"judge_model": "j/j", "scores": {"overall": 8}, "notes": "synthetic"}
    path = tmp_path / "run.json"
    path.write_text(json.dumps(run))
    # Silent synthetic PCM for container/metadata tests, never claimed to be a rendered song.
    for name in ("vocal.wav", "timbre.wav", "backing.wav"):
        with wave.open(str(tmp_path / name), "wb") as wav:
            wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            wav.writeframes(b"\0\0" * 800)
    mapping = {"version": 1, "voice_mode": "single_voice_per_clip", "clips": [
        {"start_line": 1, "end_line": 3, "source_vocal": "vocal.wav", "source_text": "source one"},
        {"start_line": 4, "end_line": 8, "source_vocal": "vocal.wav", "source_text": "source two",
         "timbre_reference": "timbre.wav", "timbre_text": "reference two", "backing": "backing.wav"},
    ]}
    map_path = tmp_path / "audio.yaml"
    map_path.write_text(yaml.safe_dump(mapping))
    return path, map_path, run, mapping


def rewrite_map(inputs):
    inputs[1].write_text(yaml.safe_dump(inputs[3]))


def rewrite_run(inputs):
    inputs[0].write_text(json.dumps(inputs[2]))


def test_export_matches_actual_upstream_jsonl_contract_and_keeps_scores(inputs, tmp_path):
    run_path, map_path, run, _ = inputs
    original = run_path.read_bytes()
    manifest_path = export_song(run_path, map_path, tmp_path / "private-export")
    manifest = json.loads(manifest_path.read_text())
    raw = (manifest_path.parent / "ying-input.jsonl").read_bytes()
    rows = [json.loads(line) for line in raw.splitlines()]
    assert run_path.read_bytes() == original
    assert manifest["run"]["sha256"] == hashlib.sha256(original).hexdigest()
    assert manifest["backend"]["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert manifest["benchmark_snapshot"]["scores"] == run["scores"]
    assert manifest["benchmark_snapshot"]["judge"] == run["judge"]
    assert manifest["status"] == "prepared_only"
    assert manifest["backend"]["rendered"] is False
    assert manifest["backend"]["model_revision"] is None
    assert manifest["rights"] == {"status": "not_verified", "user_supplied_note": None}
    assert len(rows) == 2
    assert set(rows[0]) == {"id", "melody_ref_path", "gen_text", "timbre_ref_path", "timbre_ref_text"}
    assert rows[0]["gen_text"] == "The sky is bright|We watch the light|We walk back home"
    assert rows[1]["gen_text"] == "You take the road|I take the train|We watch the light|We walk back home|Now we walk back home"
    assert rows[0]["melody_ref_path"] == str((tmp_path / "vocal.wav").resolve())
    assert rows[0]["timbre_ref_path"] == rows[0]["melody_ref_path"]
    assert rows[0]["timbre_ref_text"] == "source one"
    assert rows[1]["timbre_ref_path"] == str((tmp_path / "timbre.wav").resolve())
    assert rows[1]["timbre_ref_text"] == "reference two"
    assert manifest["clips"][0]["timbre_source"] == "source_vocal"
    assert manifest["clips"][1]["timbre_source"] == "separate_reference"
    assert manifest["clips"][1]["backing"]["frames"] == 800
    assert "backing" not in rows[1]
    assert (manifest_path.parent / ".gitignore").read_text() == "*\n!.gitignore\n"
    assert manifest_path.stat().st_mode & 0o777 == 0o600
    assert manifest_path.parent.stat().st_mode & 0o777 == 0o700


def test_performance_order_preserves_repeats_and_performers(inputs):
    before = copy.deepcopy(inputs[2])
    lines = performed_lines(inputs[2])
    assert [x["section"] for x in lines] == ["opening", "refrain", "refrain", "exchange", "exchange", "refrain", "refrain", "ending"]
    assert [x["performance_index"] for x in lines] == [1, 2, 2, 3, 3, 4, 4, 5]
    assert [x["sung_by"] for x in lines] == [[1], [1, 2], [1, 2], [1], [2], [1, 2], [1, 2], [2]]
    assert inputs[2] == before


def test_snapshot_not_current_template_is_used(inputs):
    run = inputs[2]
    run["config"]["spec"] = "path-that-does-not-exist.yaml"
    run["spec_snapshot"]["performance_order"] = ["ending", "opening", "exchange", "refrain"]
    assert [x["section"] for x in performed_lines(run)] == ["ending", "opening", "exchange", "exchange", "refrain", "refrain"]


def test_given_sections_are_included_but_remain_given(inputs):
    inputs[2]["parts"]["refrain"]["author"] = "fixed"
    lines = performed_lines(inputs[2])
    assert [x["author"] for x in lines if x["section"] == "refrain"] == ["fixed"] * 4


@pytest.mark.parametrize("change", [
    lambda r: r.update(failed={"error": "failed"}),
    lambda r: r.pop("spec_snapshot"),
    lambda r: r.update(version=1),
    lambda r: r["parts"]["opening"].update(lines=[]),
    lambda r: r["parts"]["opening"].update(lines=["one", "two"]),
    lambda r: r["parts"].pop("ending"),
    lambda r: r["parts"]["opening"].update(lines=[" "]),
    lambda r: r["parts"]["opening"].update(lines=["one\ntwo"]),
    lambda r: r["parts"]["opening"].update(lines=["one|two"]),
    lambda r: r["parts"]["opening"].update(lines=["one <adlib>two</adlib>"]),
    lambda r: r["parts"]["exchange"].update(author=[1]),
    lambda r: r.pop("scores"),
])
def test_ambiguous_or_incomplete_run_rejected(inputs, tmp_path, change):
    change(inputs[2])
    rewrite_run(inputs)
    out = tmp_path / "out"
    with pytest.raises(ValueError):
        export_song(inputs[0], inputs[1], out)
    assert not out.exists()


@pytest.mark.parametrize("change", [
    lambda m: m.update(version=True),
    lambda m: m.update(voice_mode="choir"),
    lambda m: m.update(clips=[]),
    lambda m: m.update(unknown="typo"),
    lambda m: m["clips"][0].update(start_line=2),
    lambda m: m["clips"][0].update(start_line=True),
    lambda m: m["clips"][0].update(end_line=9),
    lambda m: m["clips"][0].update(end_line=0),
    lambda m: m["clips"][1].update(start_line=3),
    lambda m: m["clips"][1].update(start_line=5),
    lambda m: m["clips"][1].update(end_line=7),
    lambda m: m["clips"][0].update(source_text=""),
    lambda m: m["clips"][0].update(timbre_reference="timbre.wav"),
    lambda m: m["clips"][0].update(timbre_text="unpaired"),
    lambda m: m["clips"][0].update(source_vocal="missing.wav"),
    lambda m: m["clips"][0].update(unknown="typo"),
])
def test_invalid_audio_maps_rejected_before_writes(inputs, tmp_path, change):
    change(inputs[3])
    rewrite_map(inputs)
    out = tmp_path / "out"
    with pytest.raises(ValueError):
        export_song(inputs[0], inputs[1], out)
    assert not out.exists()


def test_duplicate_yaml_keys_rejected(inputs):
    inputs[1].write_text("version: 1\nversion: 2\n")
    with pytest.raises(ValueError, match="unique"):
        prepare_export(inputs[0], inputs[1])


@pytest.mark.parametrize("contents", [b"not a wav", b"RIFF\x01\x00\x00\x00WAVE"])
def test_non_audio_rejected(inputs, tmp_path, contents):
    (tmp_path / "vocal.wav").write_bytes(contents)
    with pytest.raises(ValueError, match="PCM WAV"):
        prepare_export(inputs[0], inputs[1])


def test_truncated_audio_rejected(inputs, tmp_path):
    path = tmp_path / "vocal.wav"
    path.write_bytes(path.read_bytes()[:-10])
    with pytest.raises(ValueError, match="truncated"):
        prepare_export(inputs[0], inputs[1])


def test_rights_note_is_only_a_note(inputs):
    inputs[3]["rights_note"] = "I recorded these synthetic clips."
    rewrite_map(inputs)
    manifest, _ = prepare_export(inputs[0], inputs[1])
    assert manifest["rights"] == {"status": "not_verified", "user_supplied_note": "I recorded these synthetic clips."}


def test_ids_cannot_escape_output_directory(inputs):
    inputs[2]["id"] = "../../elsewhere"
    rewrite_run(inputs)
    _, rows = prepare_export(inputs[0], inputs[1])
    assert all("/" not in row["id"] and ".." not in row["id"] for row in rows)


def test_export_never_overwrites_existing_files_or_symlinks(inputs, tmp_path):
    out = tmp_path / "existing"
    out.mkdir()
    sentinel = out / "manifest.json"
    sentinel.write_text("keep")
    with pytest.raises(ValueError, match="already exists"):
        export_song(inputs[0], inputs[1], out)
    assert sentinel.read_text() == "keep"
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "does-not-exist")
    with pytest.raises(ValueError, match="already exists"):
        export_song(inputs[0], inputs[1], link)


def test_cli_offline_without_processes_or_api_calls(inputs, tmp_path, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("export must not call the network, a model, or another program")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("weird_ai_bench.cli._client", forbidden)
    monkeypatch.setattr("weird_ai_bench.cli.OpenRouterClient", forbidden)
    assert main(["export-song", str(inputs[0]), "--audio-map", str(inputs[1]),
                 "--out", str(tmp_path / "out")]) == 0
    output = capsys.readouterr().out
    assert "not been rendered" in output
    assert main(["export-song", str(inputs[0]), "--audio-map", str(inputs[1]),
                 "--out", str(tmp_path / "out")]) == 2
    assert "already exists" in capsys.readouterr().err


def test_corrupt_wav_chunk_returns_cli_error(inputs, tmp_path, capsys):
    path = tmp_path / "vocal.wav"
    contents = bytearray(path.read_bytes())
    contents[16:20] = struct.pack("<I", 0xffffffff)
    path.write_bytes(contents)
    assert main(["export-song", str(inputs[0]), "--audio-map", str(inputs[1]),
                 "--out", str(tmp_path / "out")]) == 2
    assert "PCM WAV" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()
