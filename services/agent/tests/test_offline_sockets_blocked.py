import os
import sys
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure services/agent root is first on sys.path
AGENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT))

import pytest
from agent import (
    APP_NAME,
    WAKE_WORD,
    respell_for_tts,
    is_stop_command,
    calculate_adaptive_endpointing,
    GuardedOrpheusTTS,
    LocalMockTTS,
    _RECOVERY_WAV,
    _RECOVERY_LINE_TEXT,
)


@pytest.fixture(autouse=True)
def block_all_network_sockets(monkeypatch):
    """Guarantees zero outbound network calls can occur during tests.
    Any attempt to connect an IP socket raises a fatal RuntimeError.
    """
    orig_connect = socket.socket.connect

    def forbidden_connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise RuntimeError(f"FATAL: Prohibited outbound external network call detected to {address} during offline test execution!")
        return orig_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)


def test_socket_blocker_actively_prevents_network():
    """Prove that the network blocker fixture actively traps and blocks network attempts."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(RuntimeError, match="Prohibited outbound external network call detected"):
        s.connect(("8.8.8.8", 53))


def test_offline_configuration_and_prompts_with_sockets_blocked():
    """Verify system prompt and configuration isolation execute 100% offline."""
    from agent import _SYSTEM_PROMPT_TEMPLATE
    prompt = _SYSTEM_PROMPT_TEMPLATE.replace("{{APP_NAME}}", "Daimon").replace("{{WAKE_WORD}}", "Awaken")
    assert "You are Daimon" in prompt
    assert 'Your wake word is "Awaken"' in prompt


def test_offline_respelling_logic_with_sockets_blocked():
    """Verify phonetic respelling dictionary executes 100% offline."""
    assert respell_for_tts("Hello Daimon", "Daimon", "DAY-mon") == "Hello DAY-mon"
    assert respell_for_tts("Daimon's latency", "Daimon", "DAY-mon") == "DAY-mon's latency"


def test_offline_stop_words_with_sockets_blocked():
    """Verify stop words pattern evaluation executes 100% offline."""
    assert is_stop_command("Stop immediately") is True
    assert is_stop_command("Cancel that") is True
    assert is_stop_command("Never mind") is True
    assert is_stop_command("What is the time?") is False


def test_offline_adaptive_endpointing_with_sockets_blocked():
    """Verify adaptive endpointing calculation executes 100% offline."""
    min_s, max_s = calculate_adaptive_endpointing("Stop.")
    assert min_s <= 0.4 and max_s <= 1.3
    min_l, max_l = calculate_adaptive_endpointing("Can you explain the plot of Inception to me in detail please?")
    assert min_l >= 0.75 and max_l >= 2.0


def test_offline_tts_quota_and_persistence_with_sockets_blocked(tmp_path):
    """Verify GuardedOrpheusTTS quota, persistence, and local fallback logic with sockets blocked."""
    ts_file = tmp_path / "quota.jsonl"
    guarded = GuardedOrpheusTTS(
        api_key="dummy_offline_key",
        hourly_limit=100,
        fallback_tts=LocalMockTTS(sample_rate=24000),
        timestamps_file=ts_file,
    )
    mock_stream = MagicMock()
    guarded._inner.synthesize = lambda text, conn_options=None: mock_stream
    assert guarded.hourly_request_count == 0

    # Simulate request under quota
    stream = guarded.synthesize("Offline test line")
    assert stream == mock_stream
    assert guarded.hourly_request_count == 1
    assert ts_file.exists()

    # Verify reload from disk
    guarded2 = GuardedOrpheusTTS(
        api_key="dummy_offline_key",
        hourly_limit=100,
        fallback_tts=LocalMockTTS(sample_rate=24000),
        timestamps_file=ts_file,
    )
    assert guarded2.hourly_request_count == 1


def test_offline_recovery_audio_file_integrity_with_sockets_blocked():
    """Verify pre-recorded recovery audio file exists and conforms to 24kHz mono 16-bit specs."""
    import wave
    assert _RECOVERY_WAV.exists()
    assert _RECOVERY_LINE_TEXT == "I've hit my voice limit, switching to my backup voice."
    with wave.open(str(_RECOVERY_WAV), "rb") as wf:
        assert wf.getframerate() == 24000
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
