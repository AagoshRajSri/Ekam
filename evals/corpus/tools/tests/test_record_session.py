"""
Unit tests for record_session.py using FakeAudioBackend (zero microphone dependency).
"""

from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from evals.corpus.tools.record_session import (
    FakeAudioBackend,
    compute_metrics,
    run_session,
    write_wav_24bit,
)


def test_write_and_read_24bit_wav(tmp_path):
    wav_path = tmp_path / "test_24bit.wav"
    t = np.arange(48000) / 48000.0
    tone = 0.5 * np.sin(2.0 * np.pi * 1000.0 * t).astype(np.float32)

    write_wav_24bit(wav_path, tone, 48000)
    assert wav_path.exists()

    with wave.open(str(wav_path), "rb") as wf:
        assert wf.getframerate() == 48000
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 3  # 24-bit PCM
        assert wf.getnframes() == 48000
        raw = wf.readframes(wf.getnframes())

    # Unpack 24-bit bytes
    b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
    unpacked = (
        b[:, 0].astype(np.int32)
        | (b[:, 1].astype(np.int32) << 8)
        | (b[:, 2].astype(np.int8).astype(np.int32) << 16)
    ).astype(np.float64) / 8388607.0

    # Max difference between original float and 24-bit quantization should be < 1e-6
    max_err = np.max(np.abs(unpacked - tone))
    assert max_err < 1e-5


def test_compute_metrics_clean_and_clipped():
    samplerate = 48000
    t = np.arange(int(samplerate * 2.0)) / samplerate

    # Clean tone at -12 dBFS (amp ~ 0.25)
    clean = (0.25 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
    m_clean = compute_metrics(clean, samplerate)
    assert not m_clean["is_clipped"]
    assert -13.0 <= m_clean["peak_dBFS"] <= -11.0

    # Clipped audio (amp >= 1.0)
    clipped = np.ones(samplerate, dtype=np.float32)
    m_clipped = compute_metrics(clipped, samplerate)
    assert m_clipped["is_clipped"]
    assert m_clipped["peak_dBFS"] >= -0.05


def test_record_session_with_fake_backend(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "items": [{"id": "cmd_01"}],
        "clips": [
            {
                "filename": "s01_Q_cmd_01_t1.wav",
                "id": "cmd_01",
                "section": "C",
                "env": "Q",
                "take": 1,
                "text": "Daimon what time is it",
                "condition": "natural",
            },
            {
                "filename": "s01_Q_cmd_01_t2.wav",
                "id": "cmd_01",
                "section": "C",
                "env": "Q",
                "take": 2,
                "text": "Daimon what time is it",
                "condition": "natural",
            },
        ]
    }))

    masters_dir = tmp_path / "masters"
    flags_path = tmp_path / "quality_flags.json"
    fake_backend = FakeAudioBackend()

    # Inputs:
    # Clip 1: [Enter] to start, [Enter] to accept
    # Clip 2: [Enter] to start, 'p' (playback), [Enter] to accept
    prompts = iter(["", "", "", "p", ""])

    rc = run_session(
        manifest_path=manifest_path,
        masters_dir=masters_dir,
        quality_flags_path=flags_path,
        backend=fake_backend,
        input_prompter=lambda prompt: next(prompts),
    )
    assert rc == 0
    assert (masters_dir / "s01_Q_cmd_01_t1.wav").exists()
    assert (masters_dir / "s01_Q_cmd_01_t2.wav").exists()
    assert fake_backend.recorded_count == 2
    assert fake_backend.played_count == 1  # 1 playback occurred


def test_record_session_retake_logs_quality_flag(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "items": [{"id": "cmd_01"}],
        "clips": [
            {
                "filename": "s01_Q_cmd_01_t1.wav",
                "id": "cmd_01",
                "section": "C",
                "env": "Q",
                "take": 1,
                "text": "Daimon what time is it",
                "condition": "natural",
            },
        ]
    }))

    masters_dir = tmp_path / "masters"
    flags_path = tmp_path / "quality_flags.json"

    # Audio with clipping to trigger fault
    clipped_audio = np.ones(48000, dtype=np.float32)
    fake_backend = FakeAudioBackend(fake_audio=clipped_audio)

    # First take: Enter start, 'r' redo (reason auto-detected as clipping), Second take: Enter start, Enter accept
    prompts = iter(["", "r", "", ""])

    rc = run_session(
        manifest_path=manifest_path,
        masters_dir=masters_dir,
        quality_flags_path=flags_path,
        backend=fake_backend,
        input_prompter=lambda prompt: next(prompts),
    )
    assert rc == 0
    assert (masters_dir / "s01_Q_cmd_01_t1.wav").exists()
    assert flags_path.exists()

    with open(flags_path, "r", encoding="utf-8") as f:
        flags = json.load(f)
    assert len(flags) == 1
    assert flags[0]["filename"] == "s01_Q_cmd_01_t1.wav"
    assert flags[0]["reason"] == "clipping"
