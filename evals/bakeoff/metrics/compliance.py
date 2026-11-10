"""
LLM rule compliance checker for Phase 1 voice responses.
Spec §2 / Appendix A:
- At most 2 sentences.
- Plain spoken language: no markdown (#, *, `, _, links), bullet points, lists, or emoji.
"""

from __future__ import annotations

import re
from typing import Any

# Matches markdown headings, bold, italic, inline code, links, list items
MARKDOWN_RE = re.compile(
    r"(^#{1,6}\s)|(\*\*|__|[*_])|(`[^`]+`)|(\[[^\]]+\]\([^)]+\))|(^\s*[-*+]\s)|(^\s*\d+\.\s)",
    re.MULTILINE,
)

# Matches common emoji ranges
EMOJI_RE = re.compile(
    r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\ud83c-\ud83e][\ud000-\udfff]",
    flags=re.UNICODE,
)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences handling common abbreviations."""
    clean = text.strip()
    if not clean:
        return []
    # Split by period, exclamation, question mark followed by whitespace or end
    raw_sentences = re.split(r"[.!?]+(?:\s+|$)", clean)
    return [s.strip() for s in raw_sentences if s.strip()]


def check_llm_compliance(text: str) -> dict[str, Any]:
    sentences = split_sentences(text)
    sentence_count = len(sentences)

    has_markdown = bool(MARKDOWN_RE.search(text))
    has_emoji = bool(EMOJI_RE.search(text))
    has_list = bool(re.search(r"(^\s*[-*+]\s)|(^\s*\d+\.\s)", text, re.MULTILINE))

    violates_sentence_limit = sentence_count > 2

    reasons: list[str] = []
    if violates_sentence_limit:
        reasons.append(f"Too many sentences ({sentence_count} > 2)")
    if has_markdown:
        reasons.append("Contains markdown syntax")
    if has_list:
        reasons.append("Contains list or bullet structure")
    if has_emoji:
        reasons.append("Contains emoji characters")

    is_compliant = not reasons

    return {
        "compliant": is_compliant,
        "sentence_count": sentence_count,
        "has_markdown": has_markdown,
        "has_list": has_list,
        "has_emoji": has_emoji,
        "reasons": reasons,
    }
