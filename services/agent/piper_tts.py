"""
Piper TTS Wrapper for LiveKit Agents
====================================
Local, zero-network, CPU-based speech synthesis using Piper ONNX.
Provides real local audio synthesis as a fallback to cloud TTS (Groq Orpheus).
"""

from __future__ import annotations

import io
import logging
import os
import time
from pathlib import Path
from typing import Any

import structlog
from livekit import rtc
from livekit.agents import (
    DEFAULT_API_CONNECT_OPTIONS,
    tts,
)

log = structlog.get_logger()

# Default model search path
_MODELS_DIR = Path(__file__).resolve().parent / "models"


class PiperChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        tts_instance: PiperTTS,
        input_text: str,
        conn_options: Any = None,
    ) -> None:
        super().__init__(
            tts=tts_instance,
            input_text=input_text,
            conn_options=conn_options or DEFAULT_API_CONNECT_OPTIONS,
        )
        self._piper_tts = tts_instance

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        if not self._piper_tts.is_available:
            log.warning("piper_voice_unavailable", text=self._input_text[:30])
            return

        sample_rate = self._piper_tts.sample_rate
        output_emitter.initialize(
            request_id=f"piper_{int(time.time() * 1000)}",
            sample_rate=sample_rate,
            num_channels=1,
            mime_type="audio/pcm",
            frame_size_ms=200,
            stream=False,
        )

        try:
            voice = self._piper_tts.voice
            assert voice is not None

            # Generate audio chunks using Piper
            for chunk in voice.synthesize(self._input_text):
                raw_bytes = chunk.audio_int16_bytes
                if not raw_bytes:
                    continue
                # Split into 200ms audio frames for smooth streaming
                chunk_samples = int(sample_rate * 0.2)
                chunk_bytes = chunk_samples * 2  # 16-bit mono = 2 bytes/sample
                for i in range(0, len(raw_bytes), chunk_bytes):
                    slice_data = raw_bytes[i : i + chunk_bytes]
                    samples_in_slice = len(slice_data) // 2
                    frame = rtc.AudioFrame(
                        data=slice_data,
                        sample_rate=sample_rate,
                        num_channels=1,
                        samples_per_channel=samples_in_slice,
                    )
                    output_emitter.push(frame)

            output_emitter.flush()
        except Exception as e:
            log.error("piper_synthesis_failed", error=str(e))
            output_emitter.flush()


class PiperTTS(tts.TTS):
    """Local, offline Piper TTS provider for LiveKit Agents."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        config_path: str | Path | None = None,
        sample_rate: int = 22050,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self._model_path = Path(model_path) if model_path else None
        self._config_path = Path(config_path) if config_path else None
        self._voice: Any = None
        self._load_voice()

    def _load_voice(self) -> None:
        try:
            from piper.voice import PiperVoice

            if self._model_path and self._model_path.exists():
                self._voice = PiperVoice.load(
                    model_path=str(self._model_path),
                    config_path=str(self._config_path) if self._config_path else None,
                )
                log.info("piper_voice_loaded", model=str(self._model_path))
            else:
                log.info("piper_no_model_configured", note="PiperTTS ready for model binding")
        except Exception as e:
            log.warning("piper_load_failed", error=str(e))
            self._voice = None

    @property
    def is_available(self) -> bool:
        return self._voice is not None

    @property
    def voice(self) -> Any:
        return self._voice

    def synthesize(
        self, text: str, *, conn_options: Any = None
    ) -> tts.ChunkedStream:
        return PiperChunkedStream(
            tts_instance=self,
            input_text=text,
            conn_options=conn_options,
        )

