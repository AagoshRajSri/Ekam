"""
Word Error Rate (WER) and Entity Accuracy metrics for speech-to-text evaluation.
Pure Python dynamic programming implementation. Zero external dependencies.
"""

from __future__ import annotations

import re
import string


def normalize_text(text: str) -> str:
    """Normalize text for consistent WER scoring.
    Lowercases, replaces hyphens with spaces, removes punctuation, and normalizes whitespace.
    """
    if not text:
        return ""
    text = text.lower()
    # Replace dashes/hyphens with space (e.g. 'twenty-five' -> 'twenty five')
    text = text.replace("-", " ").replace("—", " ").replace("–", " ")
    # Remove punctuation
    translator = str.maketrans("", "", string.punctuation)
    text = text.translate(translator)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Compute Word Error Rate (WER) using Levenshtein distance on word tokens.
    WER = (Substitutions + Deletions + Insertions) / len(reference_words)
    Returns a float between 0.0 and 1.0 (or > 1.0 if insertions exceed deletions).
    """
    ref_words = normalize_text(reference).split()
    hyp_words = normalize_text(hypothesis).split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    n = len(ref_words)
    m = len(hyp_words)

    # DP table: d[i][j] is distance between ref[:i] and hyp[:j]
    # Initialize with cost of deletions and insertions
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                substitution = dp[i - 1][j - 1] + 1
                deletion = dp[i - 1][j] + 1
                insertion = dp[i][j - 1] + 1
                dp[i][j] = min(substitution, deletion, insertion)

    distance = dp[n][m]
    return distance / float(n)


def entity_accuracy(expected_entities: list[str], hypothesis: str) -> float:
    """Compute fraction of expected entities found in hypothesis.
    Returns 1.0 if expected_entities is empty.
    """
    if not expected_entities:
        return 1.0

    norm_hyp = normalize_text(hypothesis)
    found_count = 0

    for ent in expected_entities:
        norm_ent = normalize_text(ent)
        if norm_ent and norm_ent in norm_hyp:
            found_count += 1

    return found_count / float(len(expected_entities))
