"""
Unit tests for latency percentiles and LLM rule compliance.
Zero external API calls.
"""

from __future__ import annotations

from evals.bakeoff.metrics.compliance import check_llm_compliance
from evals.bakeoff.metrics.latency import compute_percentiles


def test_compute_percentiles():
    data = [100.0, 200.0, 300.0, 400.0, 500.0]
    p = compute_percentiles(data)
    assert p["count"] == 5
    assert p["p50"] == 300.0
    assert p["min"] == 100.0
    assert p["max"] == 500.0
    assert p["mean"] == 300.0

    # Empty list handles gracefully
    p_empty = compute_percentiles([])
    assert p_empty["count"] == 0
    assert p_empty["p50"] == 0.0


def test_llm_compliance_valid_cases():
    valid1 = "It is three o'clock. The weather is sunny."
    res1 = check_llm_compliance(valid1)
    assert res1["compliant"] is True
    assert res1["sentence_count"] == 2

    valid2 = "One hundred thirty-four thousand and forty-three."
    res2 = check_llm_compliance(valid2)
    assert res2["compliant"] is True
    assert res2["sentence_count"] == 1


def test_llm_compliance_violations():
    # > 2 sentences
    long_reply = "First sentence here. Second sentence follows. Third sentence breaks the rule."
    res = check_llm_compliance(long_reply)
    assert res["compliant"] is False
    assert res["sentence_count"] == 3
    assert any("Too many sentences" in r for r in res["reasons"])

    # Markdown syntax
    markdown_reply = "Here is **bold** text and `code`."
    res_md = check_llm_compliance(markdown_reply)
    assert res_md["compliant"] is False
    assert res_md["has_markdown"] is True

    # Bullet list
    list_reply = "Here are items:\n- Item one\n- Item two"
    res_list = check_llm_compliance(list_reply)
    assert res_list["compliant"] is False
    assert res_list["has_list"] is True

    # Emoji
    emoji_reply = "Sure thing! 😊"
    res_emoji = check_llm_compliance(emoji_reply)
    assert res_emoji["compliant"] is False
    assert res_emoji["has_emoji"] is True
