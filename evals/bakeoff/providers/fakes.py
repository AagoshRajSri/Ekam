"""
Offline fake providers for testing and dry-run execution.
Guarantees tests make ZERO external API calls.
"""

from __future__ import annotations

import math
import struct
import time
import wave
from pathlib import Path
from typing import Any

from evals.bakeoff.providers.base import LLMProvider, STTProvider, TTSProvider


class FakeSTTProvider(STTProvider):
    def __init__(self, candidate_id: str = "fake_stt", config: dict[str, Any] | None = None, ground_truth: dict[str, Any] | None = None) -> None:
        super().__init__(candidate_id, config or {})
        self.ground_truth = ground_truth or {}

    def transcribe(self, wav_path: Path) -> dict[str, Any]:
        fname = wav_path.name
        t0 = time.monotonic()
        # Look up text in ground truth if available, otherwise dummy text
        gt_entry = self.ground_truth.get(fname, {})
        text = gt_entry.get("text", "Daimon what time is it")
        rtt_ms = 45.0  # Simulated fast local response

        return {
            "text": text,
            "rtt_ms": rtt_ms,
            "raw_response": {"fake": True, "file": fname},
        }


class FakeLLMProvider(LLMProvider):
    def __init__(self, candidate_id: str = "fake_llm", config: dict[str, Any] | None = None) -> None:
        super().__init__(candidate_id, config or {})

    def generate(self, user_prompt: str, system_prompt: str) -> dict[str, Any]:
        t0 = time.monotonic()
        # Returns a clean, compliant 1-sentence reply with no markdown or emoji
        text = "It is three o'clock in Tokyo."
        ttft_ms = 120.0
        total_ms = 210.0

        return {
            "text": text,
            "ttft_ms": ttft_ms,
            "total_ms": total_ms,
            "token_count": 8,
        }


class FakeTTSProvider(TTSProvider):
    def __init__(self, candidate_id: str = "fake_tts", config: dict[str, Any] | None = None) -> None:
        super().__init__(candidate_id, config or {})
        self.request_count = 0

    def synthesize(self, text: str, output_wav: Path) -> dict[str, Any]:
        self.request_count += 1
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        sample_rate = 24000
        duration_s = 1.0
        nframes = int(sample_rate * duration_s)

        with wave.open(str(output_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            samples = [int(5000.0 * math.sin(2 * math.pi * 440 * (i / sample_rate))) for i in range(nframes)]
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))

        ttfb_ms = 95.0
        total_ms = 150.0
        rtf = (total_ms / 1000.0) / duration_s

        return {
            "ttfb_ms": ttfb_ms,
            "total_ms": total_ms,
            "audio_duration_s": duration_s,
            "rtf": round(rtf, 3),
        }
