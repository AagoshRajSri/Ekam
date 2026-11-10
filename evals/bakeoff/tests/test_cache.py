"""
Unit tests for the resumable bake-off cache.
Zero external API calls.
"""

from __future__ import annotations

from evals.bakeoff.cache import BakeoffCache, compute_hash


def test_cache_set_and_get(tmp_path):
    cache = BakeoffCache(tmp_path)
    assert cache.count() == 0

    cid = "test_cand"
    inp_hash = compute_hash("test input text")
    data = {"text": "output text", "rtt_ms": 120.0}

    cache.set(cid, inp_hash, data)
    assert cache.count() == 1

    retrieved = cache.get(cid, inp_hash)
    assert retrieved == data
    assert retrieved["text"] == "output text"

    # Missing entry returns None
    missing = cache.get(cid, "nonexistent_hash")
    assert missing is None


def test_cache_persists_across_instances(tmp_path):
    cache1 = BakeoffCache(tmp_path)
    inp_hash = compute_hash("sample 1")
    cache1.set("provider_a", inp_hash, {"val": 42})

    # New instance pointing to same directory loads persisted data
    cache2 = BakeoffCache(tmp_path)
    assert cache2.count() == 1
    assert cache2.get("provider_a", inp_hash) == {"val": 42}
