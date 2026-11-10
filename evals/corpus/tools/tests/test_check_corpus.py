"""
Tests for check_corpus.py and assign_split.py using synthetic WAV files.
Zero external API calls.
"""

from __future__ import annotations

import json
import math
import struct
import sys
import tempfile
import wave
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

import check_corpus
import assign_split


def create_synthetic_wav(
    path: Path,
    framerate: int = 16000,
    nchannels: int = 1,
    sampwidth: int = 2,
    duration_s: float = 2.0,
    amplitude: float = 10000.0,
    clip: bool = False,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    nframes = int(framerate * duration_s)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(nchannels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)

        samples = []
        for i in range(nframes):
            t = i / framerate
            # 0.5s quiet lead & trail, tone in middle
            if t < 0.5 or t > (duration_s - 0.5):
                val = 0
            else:
                if clip:
                    val = 32767
                else:
                    val = int(amplitude * math.sin(2 * math.pi * 440 * t))
            samples.append(val)

        raw = struct.pack(f"<{len(samples)}h", *samples)
        wf.writeframes(raw)
    return path


class Args:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_validate_valid_derived_wav(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "items": [{"id": "wake_01"}],
        "clips": [{"filename": "s01_Q_wake_01_t1.wav", "id": "wake_01"}]
    }))

    wav_dir = tmp_path / "wavs"
    wav_path = wav_dir / "s01_Q_wake_01_t1.wav"
    create_synthetic_wav(wav_path, framerate=16000, duration_s=2.0, amplitude=15000.0)

    args = Args(manifest=str(manifest_path), dir=str(wav_dir), mode="derived")
    rc = check_corpus.run_validate(args)
    assert rc == 0


def test_validate_clipped_audio_fails(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "items": [{"id": "wake_01"}],
        "clips": [{"filename": "s01_Q_wake_01_t1.wav", "id": "wake_01"}]
    }))

    wav_dir = tmp_path / "wavs"
    wav_path = wav_dir / "s01_Q_wake_01_t1.wav"
    create_synthetic_wav(wav_path, framerate=16000, clip=True)

    args = Args(manifest=str(manifest_path), dir=str(wav_dir), mode="derived")
    rc = check_corpus.run_validate(args)
    assert rc == 1  # Clipped must return error exit code 1


def test_validate_invalid_framerate_fails(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "items": [{"id": "wake_01"}],
        "clips": [{"filename": "s01_Q_wake_01_t1.wav", "id": "wake_01"}]
    }))

    wav_dir = tmp_path / "wavs"
    wav_path = wav_dir / "s01_Q_wake_01_t1.wav"
    # Derived must be 16000 Hz, 44100 Hz must fail
    create_synthetic_wav(wav_path, framerate=44100)

    args = Args(manifest=str(manifest_path), dir=str(wav_dir), mode="derived")
    rc = check_corpus.run_validate(args)
    assert rc == 1


def test_validate_bad_filename_fails(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "items": [{"id": "wake_01"}],
        "clips": []
    }))

    wav_dir = tmp_path / "wavs"
    wav_path = wav_dir / "bad_name.wav"
    create_synthetic_wav(wav_path, framerate=16000)

    args = Args(manifest=str(manifest_path), dir=str(wav_dir), mode="derived")
    rc = check_corpus.run_validate(args)
    assert rc == 1


def test_derive_masters_to_derived(tmp_path):
    masters_dir = tmp_path / "masters"
    wavs_dir = tmp_path / "wavs"

    master_wav = masters_dir / "s01_Q_wake_01_t1.wav"
    # 48000 Hz master
    create_synthetic_wav(master_wav, framerate=48000, duration_s=2.0)

    args = Args(masters_dir=str(masters_dir), wavs_dir=str(wavs_dir), force=False)
    rc = check_corpus.run_derive(args)
    assert rc == 0

    derived_wav = wavs_dir / "s01_Q_wake_01_t1.wav"
    assert derived_wav.exists()
    with wave.open(str(derived_wav), "rb") as wf:
        assert wf.getframerate() == 16000
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2


def test_resampling_anti_alias():
    """Verify that scipy.signal.resample_poly preserves 1 kHz and strongly attenuates
    tones above the 8 kHz Nyquist limit when downsampling 48 kHz -> 16 kHz.
    """
    import numpy as np
    from check_corpus import resample_to_16k

    fs = 48000
    t = np.arange(fs, dtype=np.float64) / fs
    # Pure 1 kHz tone
    tone1k = np.sin(2.0 * np.pi * 1000.0 * t)
    # Pure 10 kHz tone (above 8 kHz Nyquist of 16 kHz)
    tone10k = np.sin(2.0 * np.pi * 10000.0 * t)

    res1k = resample_to_16k(tone1k, fs)
    res10k = resample_to_16k(tone10k, fs)

    # Trim filter transient edges (100 samples)
    amp1k = float(np.sqrt(np.mean(res1k[100:-100] ** 2)) / (1.0 / np.sqrt(2.0)))
    amp10k = float(np.sqrt(np.mean(res10k[100:-100] ** 2)) / (1.0 / np.sqrt(2.0)))

    atten1k_dB = 20.0 * math.log10(amp1k)
    atten10k_dB = 20.0 * math.log10(amp10k)

    # 1 kHz must be preserved within 0.1 dB
    assert abs(atten1k_dB) < 0.1, f"1 kHz tone altered: {atten1k_dB:.3f} dB"
    # 10 kHz must be strongly attenuated by >= 40 dB (measured ~57 dB)
    assert atten10k_dB <= -40.0, f"10 kHz tone not sufficiently attenuated: {atten10k_dB:.2f} dB"


def test_assign_split_behavior(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "items": [
            {"id": "cmd_01", "section": "C", "env": "Q", "text": "test 1", "expected_action": "route_to_llm", "policy_status": "settled"},
            {"id": "cmd_02", "section": "C", "env": "Q", "text": "test 2", "expected_action": "route_to_llm", "policy_status": "settled"},
            {"id": "cmd_03", "section": "C", "env": "Q", "text": "test 3", "expected_action": "route_to_llm", "policy_status": "settled"},
        ],
        "clips": [
            {"filename": "s01_Q_cmd_01_t1.wav", "id": "cmd_01", "section": "C", "env": "Q", "take": 1, "text": "test 1", "expected_action": "route_to_llm", "policy_status": "settled"},
            {"filename": "s01_Q_cmd_01_t2.wav", "id": "cmd_01", "section": "C", "env": "Q", "take": 2, "text": "test 1", "expected_action": "route_to_llm", "policy_status": "settled"},
            {"filename": "s01_Q_cmd_02_t1.wav", "id": "cmd_02", "section": "C", "env": "Q", "take": 1, "text": "test 2", "expected_action": "route_to_llm", "policy_status": "settled"},
            {"filename": "s01_Q_cmd_02_t2.wav", "id": "cmd_02", "section": "C", "env": "Q", "take": 2, "text": "test 2", "expected_action": "route_to_llm", "policy_status": "settled"},
            {"filename": "s01_Q_cmd_03_t1.wav", "id": "cmd_03", "section": "C", "env": "Q", "take": 1, "text": "test 3", "expected_action": "route_to_llm", "policy_status": "settled"},
            {"filename": "s01_Q_cmd_03_t2.wav", "id": "cmd_03", "section": "C", "env": "Q", "take": 2, "text": "test 3", "expected_action": "route_to_llm", "policy_status": "settled"},
        ]
    }))

    gt_path = tmp_path / "ground_truth.json"
    lock_path = tmp_path / "split.lock"

    rc = assign_split.assign_split(
        manifest_path=manifest_path,
        ground_truth_path=gt_path,
        lock_path=lock_path,
        seed=42,
    )
    assert rc == 0
    assert gt_path.exists()
    assert lock_path.exists()

    with open(gt_path, "r") as f:
        gt = json.load(f)

    # Both takes of cmd_01 must be in same split
    assert gt["s01_Q_cmd_01_t1.wav"]["split"] == gt["s01_Q_cmd_01_t2.wav"]["split"]
    assert gt["s01_Q_cmd_02_t1.wav"]["split"] == gt["s01_Q_cmd_02_t2.wav"]["split"]
    assert gt["s01_Q_cmd_03_t1.wav"]["split"] == gt["s01_Q_cmd_03_t2.wav"]["split"]

    # Now simulate a test result run
    with open(lock_path, "r") as f:
        lock_data = json.load(f)
    lock_data["result_runs"] = 1
    with open(lock_path, "w") as f:
        json.dump(lock_data, f)

    # Re-running assign_split without force must refuse (return 1)
    rc_refuse = assign_split.assign_split(
        manifest_path=manifest_path,
        ground_truth_path=gt_path,
        lock_path=lock_path,
        seed=42,
    )
    assert rc_refuse == 1


def test_validate_masters_flag(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "items": [{"id": "wake_01"}],
        "clips": [{"filename": "s01_Q_wake_01_t1.wav", "id": "wake_01"}]
    }))

    masters_dir = tmp_path / "masters"
    create_synthetic_wav(
        masters_dir / "s01_Q_wake_01_t1.wav",
        framerate=48000,
        sampwidth=3,  # 24-bit
        duration_s=2.0,
    )

    # Calling with --masters flag
    args = Args(
        masters=True,
        mode="derived",
        dir=str(tmp_path / "wavs"),
        manifest=str(manifest_path),
    )
    # run_validate should override dir to masters and mode to master
    rc = check_corpus.run_validate(args)
    assert rc == 0
    assert args.mode == "master"
    assert args.dir == "evals/corpus/masters" or "masters" in args.dir
