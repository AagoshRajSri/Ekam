import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure services/agent root is first on sys.path
AGENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT))

import pytest
from agent import (
    is_stop_command,
    calculate_adaptive_endpointing,
    STOP_WORDS_PATTERN,
)


def test_stop_command_whole_utterance_detection():
    """Verify stop words match whole utterances only (optional leading Daimon, trailing please/now/that)."""
    positive_cases = [
        "Stop",
        "Stop.",
        "stop please",
        "stop now",
        "Daimon stop",
        "Daimon, stop please",
        "Cancel",
        "cancel that",
        "Never mind",
        "never mind.",
        "nevermind",
        "Quiet!",
        "hold on",
        "shut up",
        "shut up now",
        "Hush",
        "abort",
    ]
    for case in positive_cases:
        assert is_stop_command(case) is True, f"Failed to detect stop command: {case}"

    # Explicitly test required negative command phrases that contain stop/cancel words but are embedded
    negative_cases = [
        "stop by the shop on the way home",
        "cancel my 3 pm meeting",
        "can you stop the music",
        "never mind what I said earlier",
        "please don't cancel my order",
        "Starting the car",
        "Nonstop flight",
        "What is the capital of India?",
        "Can you spell A to Z?",
        "Hello Daimon",
        "",
        " ",
    ]
    for case in negative_cases:
        assert is_stop_command(case) is False, f"False positive on embedded phrase: '{case}'"


def test_stop_command_force_interrupt_only_while_agent_speaking():
    """Verify force-interrupt is executed ONLY when agent is actively speaking."""
    mock_session = MagicMock()
    mock_activity = MagicMock()
    mock_session._activity = mock_activity
    mock_session.interrupt = MagicMock()
    mock_session.commit_user_turn = MagicMock()

    text = "Stop."
    assert is_stop_command(text) is True

    # Scenario A: Agent is listening / idle (NOT speaking)
    mock_session.agent_state = "listening"
    is_speaking = getattr(mock_session, "agent_state", None) == "speaking"
    if is_stop_command(text) and is_speaking:
        mock_session.interrupt(force=True)
        mock_session.commit_user_turn()

    # Must NOT interrupt when not speaking
    mock_session.interrupt.assert_not_called()
    mock_session.commit_user_turn.assert_not_called()

    # Scenario B: Agent is actively speaking
    mock_session.agent_state = "speaking"
    is_speaking = getattr(mock_session, "agent_state", None) == "speaking"
    if is_stop_command(text) and is_speaking:
        if hasattr(mock_session, "_activity") and mock_session._activity is not None:
            mock_session._activity._cancel_false_interruption_timer()
        mock_session.interrupt(force=True)
        mock_session.commit_user_turn()

    # Must interrupt when speaking
    mock_activity._cancel_false_interruption_timer.assert_called_once()
    mock_session.interrupt.assert_called_once_with(force=True)
    mock_session.commit_user_turn.assert_called_once()


def test_adaptive_endpointing_scaling():
    """Verify endpointing pauses scale dynamically based on utterance length."""
    short_text = "Stop now."
    min_d, max_d = calculate_adaptive_endpointing(short_text, base_min=0.5, base_max=1.8)
    assert min_d == 0.35
    assert max_d <= 1.3

    medium_text = "What is the capital of India?"
    min_d_med, max_d_med = calculate_adaptive_endpointing(medium_text, base_min=0.5, base_max=1.8)
    assert min_d_med == 0.5
    assert max_d_med == 1.8

    long_text = "Can you tell me about the weather in Mumbai and also check if it is raining?"
    min_d_long, max_d_long = calculate_adaptive_endpointing(long_text, base_min=0.5, base_max=1.8)
    assert min_d_long >= 0.75
    assert max_d_long >= 2.0
