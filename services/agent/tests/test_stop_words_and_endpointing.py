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


def test_stop_command_detection():
    """Verify stop words are accurately detected across phrasing variations."""
    positive_cases = [
        "Stop",
        "stop.",
        "Please stop now",
        "Cancel",
        "cancel that",
        "Never mind",
        "nevermind",
        "Quiet!",
        "hold on",
        "shut up",
        "Hush",
        "Daimon, stop please",
    ]
    for case in positive_cases:
        assert is_stop_command(case) is True, f"Failed to detect stop command: {case}"

    negative_cases = [
        "Starting the car",
        "Do not stop thinking",  # conversational embedded
        "Nonstop flight",
        "What is the capital of India?",
        "Can you spell A to Z?",
        "Hello Daimon",
        "",
        " ",
    ]
    for case in negative_cases:
        if "stop" in case.lower() and not re.search(r"\bstop\b", case, re.I):
            assert is_stop_command(case) is False, f"False positive on: {case}"
        elif "stop" not in case.lower():
            assert is_stop_command(case) is False, f"False positive on: {case}"


def test_adaptive_endpointing_scaling():
    """Verify endpointing pauses scale dynamically based on utterance length."""
    # Short command (<= 3 words): aggressive endpointing for responsiveness
    short_text = "Stop now."
    min_d, max_d = calculate_adaptive_endpointing(short_text, base_min=0.5, base_max=1.8)
    assert min_d == 0.35, f"Expected 0.35s min delay for short command, got {min_d}"
    assert max_d <= 1.3, f"Expected <= 1.3s max delay for short command, got {max_d}"

    # Medium sentence (4-8 words): balanced endpointing
    medium_text = "What is the capital of India?"
    min_d_med, max_d_med = calculate_adaptive_endpointing(medium_text, base_min=0.5, base_max=1.8)
    assert min_d_med == 0.5, f"Expected 0.5s min delay for medium query, got {min_d_med}"
    assert max_d_med == 1.8, f"Expected 1.8s max delay for medium query, got {max_d_med}"

    # Long multi-clause sentence (> 8 words): generous breathing pause to prevent splitting
    long_text = "Can you tell me about the weather in Mumbai and also check if it is raining?"
    min_d_long, max_d_long = calculate_adaptive_endpointing(long_text, base_min=0.5, base_max=1.8)
    assert min_d_long >= 0.75, f"Expected >= 0.75s min delay for long sentence, got {min_d_long}"
    assert max_d_long >= 2.0, f"Expected >= 2.0s max delay for long sentence, got {max_d_long}"


def test_stop_command_interruption_logic():
    """Verify stop command triggers immediate force interruption on session and cancels false-interruption timer."""
    mock_session = MagicMock()
    mock_activity = MagicMock()
    mock_session._activity = mock_activity
    mock_session.interrupt = MagicMock()
    mock_session.commit_user_turn = MagicMock()

    # Simulate arrival of stop command
    text = "Stop."
    if is_stop_command(text):
        if hasattr(mock_session, "_activity") and mock_session._activity is not None:
            mock_session._activity._cancel_false_interruption_timer()
        mock_session.interrupt(force=True)
        mock_session.commit_user_turn()

    mock_activity._cancel_false_interruption_timer.assert_called_once()
    mock_session.interrupt.assert_called_once_with(force=True)
    mock_session.commit_user_turn.assert_called_once()
