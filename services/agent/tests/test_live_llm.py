"""
Live LLM tier tests — opt-in only, skipped by default.
Run manually in PowerShell:
  $env:RUN_LIVE_LLM_TESTS=1; uv run --directory services/agent pytest tests/test_live_llm.py -v -s
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

SKIP_REASON = (
    "Skipping manual live LLM test by default. "
    "To run: $env:RUN_LIVE_LLM_TESTS=1; uv run --directory services/agent pytest tests/test_live_llm.py -v -s"
)


@pytest.mark.skipif(not os.getenv("RUN_LIVE_LLM_TESTS"), reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_gemini_tier_responds():
    """Verify Gemini 3.8 Flash responds with a real key and measure TTFT."""
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY / GEMINI_API_KEY not configured")

    from livekit.agents import llm
    from livekit.agents.utils import http_context
    from livekit.plugins import google

    async with http_context.open():
        gemini = google.LLM(
            model="gemini-3.8-flash",
            api_key=api_key,
            temperature=0.4,
        )

        ctx = llm.ChatContext()
        ctx.add_message(role="user", content="Respond with exactly one word: Ready.")

        t0 = time.monotonic()
        first_token_time: float | None = None
        full_text = []

        stream = gemini.chat(chat_ctx=ctx)
        async for chunk in stream:
            if first_token_time is None:
                first_token_time = time.monotonic()
            content = chunk.delta.content if (chunk.delta and chunk.delta.content) else ""
            if content:
                full_text.append(content)

        total_time = time.monotonic() - t0
        ttft = (first_token_time - t0) if first_token_time else total_time
        reply = "".join(full_text).strip()

        print(f"\n[Gemini 3.8 Flash] TTFT: {ttft * 1000:.1f} ms | Total: {total_time * 1000:.1f} ms | Reply: {reply!r}")
        assert len(reply) > 0, "Gemini returned empty text"


@pytest.mark.skipif(not os.getenv("RUN_LIVE_LLM_TESTS"), reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_ollama_first_token_latency():
    """Verify Ollama qwen2.5:7b responds and measure first-token latency vs 5.0s attempt_timeout."""
    import urllib.request

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    tags_url = base_url.replace("/v1", "/api/tags")

    # Fast ping to check if Ollama daemon is running
    try:
        with urllib.request.urlopen(tags_url, timeout=1.0) as resp:
            if resp.status != 200:
                pytest.skip("Ollama daemon returned non-200")
    except Exception:
        pytest.skip("Ollama daemon not running at localhost:11434 (start with: ollama serve)")

    from livekit.agents import llm
    from livekit.agents.utils import http_context
    from livekit.plugins import openai

    async with http_context.open():
        ollama_llm = openai.LLM(
            model="qwen2.5:7b",
            base_url=base_url,
            api_key="ollama",
            temperature=0.4,
        )

        ctx = llm.ChatContext()
        ctx.add_message(role="user", content="Respond with exactly one word: Ready.")

        t0 = time.monotonic()
        first_token_time: float | None = None
        full_text = []

        stream = ollama_llm.chat(chat_ctx=ctx)
        async for chunk in stream:
            if first_token_time is None:
                first_token_time = time.monotonic()
            content = chunk.delta.content if (chunk.delta and chunk.delta.content) else ""
            if content:
                full_text.append(content)

        total_time = time.monotonic() - t0
        ttft = (first_token_time - t0) if first_token_time else total_time
        reply = "".join(full_text).strip()

        print(f"\n[Ollama qwen2.5:7b] TTFT: {ttft * 1000:.1f} ms | Total: {total_time * 1000:.1f} ms | Reply: {reply!r}")
        print(f"FallbackAdapter attempt_timeout: 5000 ms | Margin: {5000 - ttft * 1000:.1f} ms")

        assert len(reply) > 0, "Ollama returned empty text"
        if ttft > 4.0:
            print(f"WARNING: TTFT {ttft:.2f}s is dangerously close to or exceeds the 5.0s attempt_timeout threshold!")
            print("Recommendation: Use Ollama model keep-alive (--keep-alive=24h) or increase attempt_timeout.")
