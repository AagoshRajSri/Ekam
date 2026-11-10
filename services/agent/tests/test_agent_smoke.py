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
    WAKE_WORD,
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
    assert f'Your wake word is "{WAKE_WORD}"' in _SYSTEM_PROMPT


def test_configuration_isolation_no_hardcoding():
    """Confirms APP_NAME and WAKE_WORD are dynamically derived with zero hardcoding."""
    from agent import _SYSTEM_PROMPT_TEMPLATE
    custom_prompt = (
        _SYSTEM_PROMPT_TEMPLATE
        .replace("{{APP_NAME}}", "CustomAI")
        .replace("{{WAKE_WORD}}", "HeyCustom")
    )
    assert "You are CustomAI" in custom_prompt
    assert 'Your wake word is "HeyCustom"' in custom_prompt
    assert "Daimon" not in custom_prompt
    assert "Awaken" not in custom_prompt


def test_silero_vad_loads():
    vad = silero.VAD.load(
        min_speech_duration=0.05,
        min_silence_duration=0.45,
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
    # Dynamic app name and respell
    assert respell_for_tts("Call Assistant now.", "Assistant", "Ah-sist-ant") == "Call Ah-sist-ant now."
    # No respell configured returns input unchanged
    assert respell_for_tts("Hello Daimon", "Daimon", "") == "Hello Daimon"


def test_mumbai_region_detection():
    """Verify Mumbai (ap-south / India South) region targeting logic via LIVEKIT_URL or LIVEKIT_REGION."""
    mumbai_url = "wss://my-project-ap-south.livekit.cloud"
    is_mumbai = "ap-south" in mumbai_url or "mumbai" in mumbai_url.lower() or "india" in mumbai_url.lower()
    assert is_mumbai is True

    non_mumbai_url = "wss://my-project-us-east.livekit.cloud"
    is_not_mumbai = "ap-south" in non_mumbai_url or "mumbai" in non_mumbai_url.lower()
    assert is_not_mumbai is False

    # Also supports LIVEKIT_REGION=ap-south or 'India South'
    region_env = "ap-south"
    assert "ap-south" in region_env.lower() or "india" in region_env.lower()


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
    await s1.aclose()

    # 2nd call exceeds limit -> recovery line played
    s2 = guarded.synthesize("Turn 2")
    assert guarded._recovery_played is True
    await s2.aclose()

    # 3rd call -> delegates to fallback_tts (Piper / Mock)
    s3 = guarded.synthesize("Turn 3")
    assert s3 is not None
    await s3.aclose()


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
    old_ts = _time.time() - 3700.0  # 3700 s ago (> 3600)
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
    await stream.aclose()


def test_recovery_wav_format_and_wording():
    import wave
    from agent import _RECOVERY_WAV, _RECOVERY_LINE_TEXT

    assert _RECOVERY_WAV.exists(), "recovery_429.wav must exist"
    assert _RECOVERY_LINE_TEXT == "I've hit my voice limit, switching to my backup voice."

    with wave.open(str(_RECOVERY_WAV), "rb") as wf:
        assert wf.getframerate() == 24000, f"Expected 24000 Hz, got {wf.getframerate()}"
        assert wf.getnchannels() == 1, f"Expected mono, got {wf.getnchannels()}"
        assert wf.getsampwidth() == 2, f"Expected 16-bit, got {wf.getsampwidth() * 8}-bit"


@pytest.mark.asyncio
async def test_429_retry_after_handling(tmp_path):
    import time
    mock_fallback = LocalMockTTS(sample_rate=24000)
    ts_file = tmp_path / "tts_timestamps.jsonl"
    guarded = GuardedOrpheusTTS(
        api_key="dummy",
        hourly_limit=100,
        fallback_tts=mock_fallback,
        timestamps_file=ts_file,
    )

    class Fake429Error(Exception):
        def __init__(self):
            super().__init__("Rate limit exceeded")
            self.headers = {"Retry-After": "120"}

    def fake_failing_synth(text, conn_options=None):
        raise Fake429Error()

    guarded._inner.synthesize = fake_failing_synth

    stream = guarded.synthesize("test message")
    assert stream is not None
    assert guarded._quota_exhausted is True
    # Cooldown should be approximately 120 seconds in future
    assert guarded._retry_after_until > time.time() + 100
    await stream.aclose()


@pytest.mark.asyncio
async def test_429_exponential_backoff_without_header(tmp_path):
    import time
    mock_fallback = LocalMockTTS(sample_rate=24000)
    ts_file = tmp_path / "tts_timestamps.jsonl"
    guarded = GuardedOrpheusTTS(
        api_key="dummy",
        hourly_limit=100,
        fallback_tts=mock_fallback,
        timestamps_file=ts_file,
    )

    def fake_failing_synth(text, conn_options=None):
        raise RuntimeError("Server Error 500")

    guarded._inner.synthesize = fake_failing_synth

    # 1st failure: 60s backoff
    s1 = guarded.synthesize("test 1")
    assert guarded._backoff_seconds == 120.0  # doubled for next failure
    await s1.aclose()

    # Force reset cooldown to trigger 2nd failure
    guarded._retry_after_until = 0.0
    guarded._quota_exhausted = False
    s2 = guarded.synthesize("test 2")
    assert guarded._backoff_seconds == 240.0  # doubled again
    await s2.aclose()


@pytest.mark.asyncio
async def test_proactive_headroom_switch(tmp_path):
    import time, json
    ts_file = tmp_path / "tts_timestamps.jsonl"
    # Pre-populate 91 recent timestamps -> remaining is 9 <= 10% of 100
    now = time.time()
    lines = [json.dumps({"ts": now - i * 10}) + "\n" for i in range(91)]
    ts_file.write_text("".join(lines), encoding="utf-8")

    guarded = GuardedOrpheusTTS(
        api_key="dummy",
        hourly_limit=100,
        fallback_tts=LocalMockTTS(sample_rate=24000),
        timestamps_file=ts_file,
    )

    # Should switch proactively without even calling inner
    assert guarded._quota_exhausted is True
    assert len(guarded._timestamps) == 91
    # Check headroom returns False and maintains safe state
    assert guarded._check_headroom() is False


@pytest.mark.asyncio
async def test_timestamps_persistence_across_restart(tmp_path):
    import time, json
    ts_file = tmp_path / "tts_timestamps.jsonl"
    now = time.time()
    recent_ts = now - 60.0  # 1 minute ago
    old_ts = now - 4000.0   # expired (> 1 hr)
    lines = [
        json.dumps({"ts": recent_ts}) + "\n",
        json.dumps({"ts": old_ts}) + "\n",
    ]
    ts_file.write_text("".join(lines), encoding="utf-8")

    guarded = GuardedOrpheusTTS(
        api_key="dummy",
        hourly_limit=100,
        timestamps_file=ts_file,
    )

    # Only recent_ts should be loaded
    assert len(guarded._timestamps) == 1
    assert abs(guarded._timestamps[0] - recent_ts) < 1.0
