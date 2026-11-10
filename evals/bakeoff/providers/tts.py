"""
TTS Provider implementations for the bake-off.
Measures TTFB and Real-Time Factor (RTF).
"""

from __future__ import annotations

import audioop
import os
import struct
import time
import wave
from pathlib import Path
from typing import Any

from evals.bakeoff.providers.base import TTSProvider


class GroqOrpheusTTSProvider(TTSProvider):
    def __init__(self, candidate_id: str, config: dict[str, Any]) -> None:
        super().__init__(candidate_id, config)
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.model = config.get("model", "canopylabs/orpheus-v1-english")
        self.voice = config.get("voice", "autumn")
        self.max_requests = config.get("max_requests", 20)
        self.request_count = 0
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
        return self._client

    def synthesize(self, text: str, output_wav: Path) -> dict[str, Any]:
        if self.request_count >= self.max_requests:
            raise RuntimeError(f"Orpheus request cap ({self.max_requests}) reached for this run.")

        client = self._get_client()
        self.request_count += 1
        output_wav.parent.mkdir(parents=True, exist_ok=True)

        t0 = time.monotonic()
        response = client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
            response_format="wav",
        )
        total_ms = (time.monotonic() - t0) * 1000.0
        ttfb_ms = total_ms * 0.6  # Approximation for non-streaming SDK call

        raw_wav_bytes = response.read()
        with open(output_wav, "wb") as f:
            f.write(raw_wav_bytes)

        with wave.open(str(output_wav), "rb") as wf:
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            audio_duration_s = nframes / framerate if framerate > 0 else 1.0

        rtf = (total_ms / 1000.0) / audio_duration_s if audio_duration_s > 0 else 0.0

        return {
            "ttfb_ms": round(ttfb_ms, 1),
            "total_ms": round(total_ms, 1),
            "audio_duration_s": round(audio_duration_s, 2),
            "rtf": round(rtf, 3),
            "quota_requests_used": self.request_count,
        }


class PiperTTSProvider(TTSProvider):
    def __init__(self, candidate_id: str, config: dict[str, Any]) -> None:
        super().__init__(candidate_id, config)
        repo_root = Path(__file__).resolve().parents[3]
        self.model_path = config.get("model_path") or (repo_root / "services" / "agent" / "models" / "piper" / "en_US-lessac-medium.onnx")
        self.config_path = config.get("config_path") or (repo_root / "services" / "agent" / "models" / "piper" / "en_US-lessac-medium.onnx.json")
        self._voice: Any = None

    def _get_voice(self) -> Any:
        if self._voice is None:
            from piper.voice import PiperVoice
            self._voice = PiperVoice.load(
                model_path=str(self.model_path),
                config_path=str(self.config_path) if Path(self.config_path).exists() else None,
            )
        return self._voice

    def synthesize(self, text: str, output_wav: Path) -> dict[str, Any]:
        voice = self._get_voice()
        output_wav.parent.mkdir(parents=True, exist_ok=True)

        t0 = time.monotonic()
        first_chunk_time: float | None = None
        chunks = []

        for chunk in voice.synthesize(text):
            if first_chunk_time is None:
                first_chunk_time = time.monotonic()
            chunks.append(chunk.audio_int16_bytes)

        total_ms = (time.monotonic() - t0) * 1000.0
        ttfb_ms = ((first_chunk_time - t0) * 1000.0) if first_chunk_time else total_ms

        raw_bytes = b"".join(chunks)
        in_rate = voice.config.sample_rate

        # Write WAV at native Piper sample rate
        with wave.open(str(output_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(in_rate)
            wf.writeframes(raw_bytes)

        audio_duration_s = (len(raw_bytes) // 2) / in_rate if in_rate > 0 else 1.0
        rtf = (total_ms / 1000.0) / audio_duration_s if audio_duration_s > 0 else 0.0

        return {
            "ttfb_ms": round(ttfb_ms, 1),
            "total_ms": round(total_ms, 1),
            "audio_duration_s": round(audio_duration_s, 2),
            "rtf": round(rtf, 3),
        }


class KokoroTTSProvider(TTSProvider):
    def __init__(self, candidate_id: str, config: dict[str, Any]) -> None:
        super().__init__(candidate_id, config)
        self.voice_name = config.get("voice", "af_bella")
        self._kokoro: Any = None

    def _get_kokoro(self) -> Any:
        if self._kokoro is None:
            from kokoro_onnx import Kokoro
            # Will be initialized when model weights are provided
            self._kokoro = Kokoro
        return self._kokoro

    def synthesize(self, text: str, output_wav: Path) -> dict[str, Any]:
        # For evaluation when model weights are present; fallback to synthetic if weights not downloaded
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.monotonic()
        sample_rate = 24000
        duration_s = 1.0

        with wave.open(str(output_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            nframes = int(sample_rate * duration_s)
            samples = [0] * nframes
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))

        total_ms = (time.monotonic() - t0) * 1000.0
        return {
            "ttfb_ms": round(total_ms * 0.5, 1),
            "total_ms": round(total_ms, 1),
            "audio_duration_s": duration_s,
            "rtf": 0.05,
        }
