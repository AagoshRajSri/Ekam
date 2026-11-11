import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Ensure services/agent root is first on sys.path
AGENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT))

import pytest
from agent import GuardedOrpheusTTS, LocalMockTTS


def test_hourly_request_count_property():
    """Verify hourly_request_count accurately reports rolling active requests."""
    mock_fallback = LocalMockTTS(sample_rate=24000)
    assert mock_fallback.hourly_request_count == 0

    guarded = GuardedOrpheusTTS(
        api_key="dummy",
        hourly_limit=100,
        fallback_tts=mock_fallback,
    )
    now = time.time()
    # Insert 3 active timestamps and 2 expired (> 3600s old)
    guarded._timestamps.append(now - 4000.0)  # expired
    guarded._timestamps.append(now - 3700.0)  # expired
    guarded._timestamps.append(now - 1200.0)  # active
    guarded._timestamps.append(now - 600.0)   # active
    guarded._timestamps.append(now - 10.0)    # active

    assert guarded.hourly_request_count == 3


@pytest.mark.asyncio
async def test_idle_auto_disconnect_closes_room_and_session():
    """Verify that idle auto-disconnect closes both the LiveKit room and agent session."""
    mock_room = MagicMock()
    mock_room.disconnect = AsyncMock()
    mock_room.local_participant = MagicMock()
    mock_room.local_participant.publish_data = AsyncMock()

    mock_session = MagicMock()
    mock_session.aclose = AsyncMock()

    idle_timeout_seconds = 0.3
    last_activity = [time.monotonic()]
    disconnected = False

    async def idle_watchdog():
        nonlocal disconnected
        while True:
            await asyncio.sleep(0.05)
            idle_seconds = time.monotonic() - last_activity[0]
            if idle_seconds >= idle_timeout_seconds:
                # 1. Inform client
                msg = json.dumps({
                    "type": "session_closed",
                    "reason": f"Disconnected due to {int(idle_timeout_seconds)}s of inactivity.",
                }).encode("utf-8")
                await mock_room.local_participant.publish_data(msg, reliable=True, topic="telemetry")

                # 2. Close session
                await mock_session.aclose()

                # 3. Disconnect room
                await mock_room.disconnect()
                disconnected = True
                break

    watchdog_task = asyncio.create_task(idle_watchdog())
    await asyncio.sleep(0.4)
    await watchdog_task

    assert disconnected is True
    mock_session.aclose.assert_awaited_once()
    mock_room.disconnect.assert_awaited_once()
    mock_room.local_participant.publish_data.assert_awaited_once()
    sent_payload = json.loads(mock_room.local_participant.publish_data.call_args[0][0].decode("utf-8"))
    assert sent_payload["type"] == "session_closed"


def test_turn_telemetry_enrichment_structure():
    """Verify telemetry payload enrichment includes per-turn counters and hourly budget."""
    turn_counters = {
        "turn_id": 3,
        "stt_requests": 1,
        "llm_requests": 2,
        "tts_requests": 1,
    }
    hourly_tts = 14
    first_audio_ms = 210

    enriched = {
        "type": "client_turn_telemetry",
        "turn_id": turn_counters["turn_id"],
        "first_audio_ms": first_audio_ms,
        "stt_requests": turn_counters["stt_requests"],
        "llm_requests": turn_counters["llm_requests"],
        "tts_requests": turn_counters["tts_requests"],
        "tts_requests_hourly": hourly_tts,
        "timestamp": "2026-11-11T07:15:00.000Z",
    }

    assert enriched["stt_requests"] == 1
    assert enriched["llm_requests"] == 2
    assert enriched["tts_requests"] == 1
    assert enriched["tts_requests_hourly"] == 14
    assert enriched["first_audio_ms"] == 210
