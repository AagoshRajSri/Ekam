"""
STT Provider implementations for the bake-off.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from evals.bakeoff.providers.base import STTProvider


class GroqSTTProvider(STTProvider):
    def __init__(self, candidate_id: str, config: dict[str, Any]) -> None:
        super().__init__(candidate_id, config)
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.model = config.get("model", "whisper-large-v3-turbo")
        self.language = config.get("language", "en")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                from openai import OpenAI
                self._client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=self.api_key)
        return self._client

    def transcribe(self, wav_path: Path) -> dict[str, Any]:
        client = self._get_client()
        prompt = self.config.get("prompt")
        t0 = time.monotonic()
        for attempt in range(5):
            try:
                with open(wav_path, "rb") as f:
                    kwargs: dict[str, Any] = {
                        "file": (wav_path.name, f, "audio/wav"),
                        "model": self.model,
                        "language": self.language,
                        "response_format": "json",
                    }
                    if prompt:
                        kwargs["prompt"] = prompt
                    transcription = client.audio.transcriptions.create(**kwargs)
                break
            except Exception as e:
                err_str = str(e).lower()
                if ("429" in err_str or "connection" in err_str or "getaddrinfo" in err_str or "timeout" in err_str) and attempt < 4:
                    time.sleep(3.0 * (attempt + 1))
                    continue
                raise

        rtt_ms = (time.monotonic() - t0) * 1000.0
        time.sleep(0.2)  # Avoid rate burst
        text = getattr(transcription, "text", str(transcription))
        return {
            "text": text.strip(),
            "rtt_ms": round(rtt_ms, 1),
            "raw_response": str(transcription),
        }


class FasterWhisperSTTProvider(STTProvider):
    def __init__(self, candidate_id: str, config: dict[str, Any]) -> None:
        super().__init__(candidate_id, config)
        self.model_size = config.get("model", "small.en")
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, wav_path: Path) -> dict[str, Any]:
        model = self._get_model()
        t0 = time.monotonic()
        segments, info = model.transcribe(str(wav_path), beam_size=1)
        text = " ".join(seg.text for seg in segments).strip()
        rtt_ms = (time.monotonic() - t0) * 1000.0
        return {
            "text": text,
            "rtt_ms": round(rtt_ms, 1),
            "raw_response": {"language": info.language, "duration": info.duration},
        }
