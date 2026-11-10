import asyncio
import pytest
from typing import Any
from livekit.agents.llm import (
    LLM,
    LLMStream,
    ChatContext,
    ChatMessage,
    ChatChunk,
    Choice,
    ChoiceDelta,
    FallbackAdapter,
)
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions


class Failing429Stream(LLMStream):
    async def _run(self) -> None:
        # Simulate an instant 429 Rate Limit error from primary provider (e.g. Groq)
        raise RuntimeError("HTTP 429 Too Many Requests: Rate limit reached on primary LLM")


class Failing429LLM(LLM):
    def __init__(self, name: str = "MockGroq429") -> None:
        super().__init__()
        self._name = name

    @property
    def model(self) -> str:
        return "qwen/qwen3.8-27b"

    @property
    def provider(self) -> str:
        return "groq"

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: Any = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        **kwargs: Any,
    ) -> LLMStream:
        return Failing429Stream(
            llm=self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
        )


class SuccessfulFallbackStream(LLMStream):
    async def _run(self) -> None:
        # Yield successful tokens from secondary fallback provider (e.g. Gemini)
        chunk = ChatChunk(
            id="mock_chunk_1",
            delta=ChoiceDelta(
                content="Fallback LLM response: System operational.",
                role="assistant",
            ),
        )
        self._event_ch.send_nowait(chunk)


class SuccessfulFallbackLLM(LLM):
    def __init__(self, name: str = "MockGeminiSecondary") -> None:
        super().__init__()
        self._name = name

    @property
    def model(self) -> str:
        return "gemini-2.5-flash"

    @property
    def provider(self) -> str:
        return "google"

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: Any = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        **kwargs: Any,
    ) -> LLMStream:
        return SuccessfulFallbackStream(
            llm=self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
        )


@pytest.mark.asyncio
async def test_llm_fallback_adapter_on_429():
    """Verify that when the primary LLM raises 429, FallbackAdapter immediately
    routes to the secondary LLM without crashing the session.
    """
    primary_failing = Failing429LLM()
    secondary_success = SuccessfulFallbackLLM()

    # Wrap in LiveKit's native FallbackAdapter
    adapter = FallbackAdapter(
        llm=[primary_failing, secondary_success],
        attempt_timeout=2.0,
        max_retry_per_llm=0,
    )

    ctx = ChatContext()
    ctx.add_message(role="user", content="Test prompt")

    stream = adapter.chat(chat_ctx=ctx)
    received_text = ""

    async for chunk in stream:
        if chunk.delta and chunk.delta.content:
            received_text += chunk.delta.content

    assert "Fallback LLM response: System operational." in received_text
    assert adapter.provider == "google"
    await adapter.aclose()


@pytest.mark.asyncio
async def test_three_tier_llm_fallback():
    """Verify 3-tier chain: Primary (429) -> Secondary (429) -> Tertiary (200 OK)."""
    tier1 = Failing429LLM("GroqPrimary")
    tier2 = Failing429LLM("GeminiSecondary")
    tier3 = SuccessfulFallbackLLM("OllamaTertiary")

    adapter = FallbackAdapter(
        llm=[tier1, tier2, tier3],
        attempt_timeout=2.0,
        max_retry_per_llm=0,
    )

    ctx = ChatContext()
    ctx.add_message(role="user", content="Check tertiary fallback")

    stream = adapter.chat(chat_ctx=ctx)
    received_text = ""

    async for chunk in stream:
        if chunk.delta and chunk.delta.content:
            received_text += chunk.delta.content

    assert "Fallback LLM response: System operational." in received_text
    await adapter.aclose()
