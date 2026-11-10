"""
Unit tests for WER and entity accuracy calculation.
Zero external API calls.
"""

from __future__ import annotations

import pytest
from evals.bakeoff.metrics.wer import entity_accuracy, normalize_text, word_error_rate


def test_normalize_text():
    assert normalize_text("Hello, World!") == "hello world"
    assert normalize_text("Twenty-five miles") == "twenty five miles"
    assert normalize_text("   Daimon...  what's   the time?  ") == "daimon whats the time"
    assert normalize_text("") == ""


def test_word_error_rate_exact_matches():
    assert word_error_rate("hello world", "hello world") == 0.0
    assert word_error_rate("Daimon, what time is it?", "daimon what time is it") == 0.0
    assert word_error_rate("", "") == 0.0


def test_word_error_rate_substitutions_deletions_insertions():
    # 1 deletion: ref 3 words, hyp 2 words -> 1/3
    assert pytest.approx(word_error_rate("one two three", "one three"), 0.01) == 1 / 3

    # 1 insertion: ref 2 words, hyp 3 words -> 1/2
    assert pytest.approx(word_error_rate("one two", "one extra two"), 0.01) == 1 / 2

    # 1 substitution: ref 2 words, hyp 2 words (1 mismatch) -> 1/2
    assert pytest.approx(word_error_rate("one two", "one too"), 0.01) == 1 / 2

    # completely different: ref 2 words, hyp 2 different -> 2/2 = 1.0
    assert word_error_rate("cat dog", "apple banana") == 1.0


def test_entity_accuracy():
    # Both entities present
    assert entity_accuracy(["Rahul", "10 minutes"], "texting Rahul reaching in 10 minutes") == 1.0

    # 1 of 2 present
    assert entity_accuracy(["Rahul", "Mumbai"], "texting Rahul") == 0.5

    # 0 of 2 present
    assert entity_accuracy(["Tokyo", "weather"], "hello world") == 0.0

    # No entities expected -> 1.0
    assert entity_accuracy([], "any response") == 1.0
