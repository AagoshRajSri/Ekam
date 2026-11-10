import os
import sys
from pathlib import Path

# Ensure services/agent root is first on sys.path
AGENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT))

from dotenv import load_dotenv
import pytest
from livekit.plugins import silero, groq
import agent
from agent import (
    VoiceAssistant,
    APP_NAME,
    TTS_NAME_RESPELL,
    respell_for_tts,
    GuardedOrpheusTTS,
    LocalMockTTS,
    prewarm,
    _SYSTEM_PROMPT,
)
from piper_tts import PiperTTS


def test_environment_loads():
    env_path = Path(__file__).resolve().parents[3] / ".env"
    assert env_path.exists(), ".env file must exist"
    load_dotenv(env_path)
    assert os.getenv("GROQ_API_KEY"), "GROQ_API_KEY must be configured"
    assert os.getenv("LIVEKIT_URL"), "LIVEKIT_URL must be configured"
    assert os.getenv("LIVEKIT_API_KEY"), "LIVEKIT_API_KEY must be configured"
    assert os.getenv("LIVEKIT_API_SECRET"), "LIVEKIT_API_SECRET must be configured"


def test_agent_class_instantiation():
    bot = VoiceAssistant()
    assert bot is not None
    assert f"You are {APP_NAME}" in _SYSTEM_PROMPT


def test_silero_vad_loads():
    vad = silero.VAD.load(
        min_speech_duration=0.05,
        min_silence_duration=0.55,
        activation_threshold=0.5,
        sample_rate=16000,
        force_cpu=True,
    )
    assert vad is not None


def test_groq_stt_instantiates():
    stt = groq.STT(
        model="whisper-large-v3-turbo",
        language="en",
        api_key=os.environ.get("GROQ_API_KEY", "dummy"),
    )
    assert stt is not None


def test_groq_llm_instantiates():
    llm = groq.LLM(
        model="qwen/qwen3.8-27b",
        api_key=os.environ.get("GROQ_API_KEY", "dummy"),
        temperature=0.4,
        max_completion_tokens=120,
    )
    assert llm is not None


def test_groq_tts_instantiates():
    tts = groq.TTS(
        model="canopylabs/orpheus-v1-english",
        voice="autumn",
        api_key=os.environ.get("GROQ_API_KEY", "dummy"),
    )
    assert tts is not None


def test_respell_for_tts_cases():
    assert respell_for_tts("Hello, I am Daimon.", "Daimon", "Daymon") == "Hello, I am Daymon."
    assert respell_for_tts("Ask daimon about the weather.", "Daimon", "Daymon") == "Ask Daymon about the weather."
    assert respell_for_tts("DAIMON is online.", "Daimon", "Daymon") == "Daymon is online."
    # Possessive straight apostrophe
    assert respell_for_tts("That is Daimon's response.", "Daimon", "Daymon") == "That is Daymon's response."
    # Possessive curly / typographic apostrophe
    assert respell_for_tts("That is daimon’s response.", "Daimon", "Daymon") == "That is Daymon’s response."
    # Preserves words containing the name as a substring
    assert respell_for_tts("Daimonic architecture.", "Daimon", "Daymon") == "Daimonic architecture."
    # No respell configured returns input unchanged
    assert respell_for_tts("Hello Daimon", "Daimon", "") == "Hello Daimon"


@pytest.mark.asyncio
async def test_orpheus_fallback_wiring():
    mock_fallback = LocalMockTTS(sample_rate=24000)
    guarded = GuardedOrpheusTTS(
        api_key=os.environ.get("GROQ_API_KEY", "dummy"),
        hourly_limit=1,
        fallback_tts=mock_fallback,
    )
    # Monkeypatch inner to simulate successful 1st call
    guarded._inner.synthesize = lambda text, conn_options=None: LocalMockTTS().synthesize(text)
    
    # 1st call within limit
    s1 = guarded.synthesize("Turn 1")
    assert s1 is not None

    # 2nd call exceeds limit -> recovery line played
    s2 = guarded.synthesize("Turn 2")
    assert guarded._recovery_played is True

    # 3rd call -> delegates to fallback_tts (Piper / Mock)
    s3 = guarded.synthesize("Turn 3")
    assert s3 is not None


@pytest.mark.asyncio
async def test_orpheus_quota_auto_resets_after_hour():
    """After the 1-hour window expires, GuardedOrpheusTTS must resume Orpheus
    and clear the _quota_exhausted / _recovery_played flags."""
    import time as _time

    guarded = GuardedOrpheusTTS(
        api_key="dummy",
        hourly_limit=2,
    )
    # Simulate 2 requests that happened > 1 hour ago
    old_ts = _time.monotonic() - 3700  # 3700 s ago (> 3600)
    guarded._timestamps.extend([old_ts, old_ts])
    guarded._quota_exhausted = True
    guarded._recovery_played = True

    # Monkeypatch inner so synthesize doesn't actually call Groq
    guarded._inner.synthesize = lambda text, conn_options=None: LocalMockTTS().synthesize(text)

    # synthesize() should auto-reset then succeed via Orpheus (inner)
    stream = guarded.synthesize("Hello after reset")
    assert stream is not None
    assert guarded._quota_exhausted is False, "quota_exhausted must be cleared after window reset"
    assert guarded._recovery_played is False, "recovery_played must be cleared after window reset"
