"""
LLM Provider implementations for the bake-off.
Measures TTFT and total completion time on streaming chunks.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any

from evals.bakeoff.providers.base import LLMProvider


class GroqLLMProvider(LLMProvider):
    def __init__(self, candidate_id: str, config: dict[str, Any]) -> None:
        super().__init__(candidate_id, config)
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.model = config.get("model", "qwen/qwen3.8-27b")
        self.temperature = config.get("temperature", 0.4)
        self.max_tokens = config.get("max_tokens", 120)
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
        return self._client

    def generate(self, user_prompt: str, system_prompt: str) -> dict[str, Any]:
        client = self._get_client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        t0 = time.monotonic()
        first_token_time: float | None = None
        chunks: list[str] = []

        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )

        for chunk in stream:
            if first_token_time is None:
                first_token_time = time.monotonic()
            delta = chunk.choices[0].delta.content if chunk.choices else ""
            if delta:
                chunks.append(delta)

        total_time = (time.monotonic() - t0) * 1000.0
        ttft = ((first_token_time - t0) * 1000.0) if first_token_time else total_time
        text = "".join(chunks).strip()

        return {
            "text": text,
            "ttft_ms": round(ttft, 1),
            "total_ms": round(total_time, 1),
            "token_count": len(chunks),
        }


class GeminiLLMProvider(LLMProvider):
    def __init__(self, candidate_id: str, config: dict[str, Any]) -> None:
        super().__init__(candidate_id, config)
        self.api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
        self.model = config.get("model", "gemini-3.8-flash")
        self.temperature = config.get("temperature", 0.4)
        self.max_tokens = config.get("max_tokens", 120)

    def generate(self, user_prompt: str, system_prompt: str) -> dict[str, Any]:
        # Direct REST API call to Google AI Studio v1beta
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        total_time = (time.monotonic() - t0) * 1000.0
        candidates = data.get("candidates", [])
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

        # Non-streaming REST TTFT approximation is total_time
        ttft = total_time

        return {
            "text": text.strip(),
            "ttft_ms": round(ttft, 1),
            "total_ms": round(total_time, 1),
            "token_count": len(text.split()),
        }


class OllamaLLMProvider(LLMProvider):
    def __init__(self, candidate_id: str, config: dict[str, Any]) -> None:
        super().__init__(candidate_id, config)
        self.base_url = config.get("base_url", "http://localhost:11434/v1")
        self.model = config.get("model", "qwen2.5:7b")
        self.temperature = config.get("temperature", 0.4)
        self.max_tokens = config.get("max_tokens", 120)

    def generate(self, user_prompt: str, system_prompt: str) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"},
            method="POST",
        )

        t0 = time.monotonic()
        first_token_time: float | None = None
        chunks: list[str] = []

        with urllib.request.urlopen(req, timeout=15.0) as resp:
            for line in resp:
                line_str = line.decode("utf-8").strip()
                if not line_str.startswith("data: ") or line_str == "data: [DONE]":
                    continue
                if first_token_time is None:
                    first_token_time = time.monotonic()
                try:
                    chunk_obj = json.loads(line_str[6:])
                    delta = chunk_obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        chunks.append(delta)
                except Exception:
                    pass

        total_time = (time.monotonic() - t0) * 1000.0
        ttft = ((first_token_time - t0) * 1000.0) if first_token_time else total_time
        text = "".join(chunks).strip()

        return {
            "text": text,
            "ttft_ms": round(ttft, 1),
            "total_ms": round(total_time, 1),
            "token_count": len(chunks),
        }
