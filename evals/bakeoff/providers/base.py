"""
Abstract provider interfaces for STT, LLM, and TTS candidates.
"""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any


class STTProvider(abc.ABC):
    def __init__(self, candidate_id: str, config: dict[str, Any]) -> None:
        self.candidate_id = candidate_id
        self.config = config

    @abc.abstractmethod
    def transcribe(self, wav_path: Path) -> dict[str, Any]:
        """Transcribe audio from wav_path.
        Returns dict with keys: text, rtt_ms, raw_response.
        """
        pass


class LLMProvider(abc.ABC):
    def __init__(self, candidate_id: str, config: dict[str, Any]) -> None:
        self.candidate_id = candidate_id
        self.config = config

    @abc.abstractmethod
    def generate(self, user_prompt: str, system_prompt: str) -> dict[str, Any]:
        """Generate response given user_prompt and system_prompt.
        Returns dict with keys: text, ttft_ms, total_ms, token_count.
        """
        pass


class TTSProvider(abc.ABC):
    def __init__(self, candidate_id: str, config: dict[str, Any]) -> None:
        self.candidate_id = candidate_id
        self.config = config

    @abc.abstractmethod
    def synthesize(self, text: str, output_wav: Path) -> dict[str, Any]:
        """Synthesize text to output_wav.
        Returns dict with keys: ttfb_ms, total_ms, audio_duration_s, rtf.
        """
        pass
