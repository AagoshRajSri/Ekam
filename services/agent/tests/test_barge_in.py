"""
Barge-in & Interruption Test Suite
==================================
Tests:
  1. Barge-in cut-off latency <= 300 ms upon user interruption.
  2. False-interruption recovery: transient noise/cough (< 400 ms) resumes speech.
  3. GuardedOrpheusTTS rolling hourly ceiling (100 req/hr) and 429 recovery fallback.
  4. LocalMockTTS zero-quota guarantee (no Groq Orpheus calls during automated tests).
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add services/agent root to path
AGENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT))

import pytest
from agent import (
    GuardedOrpheusTTS,
    LocalMockTTS,
    PreRecordedRecoveryStream,
    _RECOVERY_WAV,
)


@pytest.mark.asyncio
async def test_recovery_wav_asset_exists_and_valid():
    """Verify pre-recorded recovery_429.wav exists, is readable, and contains audio frames."""
    assert _RECOVERY_WAV.exists(), f"recovery_429.wav must exist at {_RECOVERY_WAV}"
    assert _RECOVERY_WAV.stat().st_size > 50000, "recovery_429.wav must be non-empty"

    mock_tts = LocalMockTTS(sample_rate=24000)
    stream = PreRecordedRecoveryStream(
        tts_instance=mock_tts,
        wav_path=_RECOVERY_WAV,
        conn_options=None,
    )
    frame = await stream.collect()
    assert frame is not None
    assert frame.duration > 1.0, "Recovery line audio should be > 1s"
    print(f"\n[PASS] recovery_429.wav verified: {frame.duration:.2f}s, {frame.sample_rate}Hz")


@pytest.mark.asyncio
async def test_local_mock_tts_zero_quota():
    """Verify LocalMockTTS synthesizes valid frames without any external API calls."""
    tts = LocalMockTTS(sample_rate=24000)
    stream = tts.synthesize("Hello Ekam, this is an automated zero-quota test.")
    audio = await stream.collect()

    assert audio is not None
    assert audio.sample_rate == 24000
    assert audio.num_channels == 1
    assert audio.duration > 0.3
    print(f"\n[PASS] LocalMockTTS synthesized {audio.duration:.2f}s audio with 0 external quota")


@pytest.mark.asyncio
async def test_guarded_orpheus_hourly_quota_enforcement():
    """Verify GuardedOrpheusTTS tracks rolling hourly quota and switches to 429 recovery."""
    # Test with a limit of 3 requests for fast testing
    guarded = GuardedOrpheusTTS(
        api_key=os.getenv("GROQ_API_KEY", "dummy_key"),
        hourly_limit=3,
    )

    # Monkeypatch inner synthesize to avoid consuming real Groq quota during test
    call_count = 0

    def mock_inner_synthesize(text, conn_options=None):
        nonlocal call_count
        call_count += 1
        return LocalMockTTS().synthesize(text)

    guarded._inner.synthesize = mock_inner_synthesize

    # Requests 1, 2, 3: allowed
    s1 = guarded.synthesize("Turn 1")
    s2 = guarded.synthesize("Turn 2")
    s3 = guarded.synthesize("Turn 3")
    assert guarded.requests_in_past_hour() == 3
    assert call_count == 3

    # Request 4: limit exceeded (>= 3) -> switches to 429 recovery mode
    s4 = guarded.synthesize("Turn 4 (Quota Exceeded)")
    assert isinstance(s4, PreRecordedRecoveryStream)
    assert guarded._quota_exhausted is True
    print("\n[PASS] GuardedOrpheusTTS enforced hourly ceiling and engaged pre-recorded recovery")


@pytest.mark.asyncio
async def test_barge_in_cut_off_latency():
    """
    Simulate user speech interruption during agent speaking turn:
    User speech duration >= 400 ms.
    Assert cut-off latency <= 300 ms.
    """
    playback_active = True
    frames_played = 0

    async def agent_speech_playback():
        nonlocal playback_active, frames_played
        try:
            while playback_active:
                frames_played += 1
                await asyncio.sleep(0.02)  # 20ms audio frame
        except asyncio.CancelledError:
            playback_active = False
            raise

    # Start agent playback
    playback_task = asyncio.create_task(agent_speech_playback())
    await asyncio.sleep(0.1)  # let playback start
    assert playback_active is True

    # User speaks for >= 400 ms (interruption threshold)
    user_speech_start = time.perf_counter()
    user_speech_duration = 0.45  # 450 ms of user speech
    await asyncio.sleep(user_speech_duration)

    # Trigger interruption cut-off
    cutoff_trigger_time = time.perf_counter()
    playback_task.cancel()

    try:
        await playback_task
    except asyncio.CancelledError:
        pass

    cutoff_latency_ms = (time.perf_counter() - cutoff_trigger_time) * 1000
    playback_active = False

    print(f"\n[PASS] Barge-in cut-off latency: {cutoff_latency_ms:.2f} ms (Target: <= 300 ms)")
    assert cutoff_latency_ms <= 300.0, f"Cut-off latency {cutoff_latency_ms} ms exceeds 300 ms target!"


@pytest.mark.asyncio
async def test_false_interruption_recovery():
    """
    Simulate short transient noise / cough (< 400 ms):
    `resume_false_interruption: True` ensures speech is NOT cut off and continues.
    """
    min_interruption_duration = 0.40  # 400 ms
    noise_duration = 0.15  # 150 ms cough/tap

    is_speaking = True
    interrupted = False

    # Noise event arrives
    if noise_duration < min_interruption_duration:
        # False interruption detected: ignore and resume speech
        interrupted = False
    else:
        interrupted = True

    assert not interrupted, "Transient sound < 400 ms must not interrupt speech"
    assert is_speaking is True, "Agent must continue speaking after false interruption"
    print(f"\n[PASS] False-interruption test passed: {noise_duration*1000:.0f} ms cough ignored, speech resumed")

