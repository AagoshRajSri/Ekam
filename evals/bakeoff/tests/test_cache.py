"""
Unit tests for the resumable bake-off cache with strict provenance.
Tests mode separation (real vs fake), separate directories, and refusal of fakes in real runs.
Zero external API calls.
"""

from __future__ import annotations

import pytest
from evals.bakeoff.cache import BakeoffCache, FakeEntryInRealRunError, compute_hash


def test_cache_set_and_get_real_mode(tmp_path):
    cache = BakeoffCache(tmp_path, mode="real")
    assert cache.count() == 0
    assert cache.cache_dir.name == "real"

    cid = "test_cand"
    inp_hash = compute_hash("test input text")
    data = {"text": "real output text", "rtt_ms": 250.0, "raw_response": {"id": "req_123"}}

    cache.set(cid, inp_hash, data)
    assert cache.count() == 1

    retrieved = cache.get(cid, inp_hash)
    assert retrieved == data
    assert retrieved["text"] == "real output text"

    # Missing entry returns None
    assert cache.get(cid, "nonexistent_hash") is None


def test_cache_separate_directories_for_real_and_fake(tmp_path):
    cache_real = BakeoffCache(tmp_path, mode="real")
    cache_fake = BakeoffCache(tmp_path, mode="fake")

    assert cache_real.cache_dir != cache_fake.cache_dir
    assert cache_real.cache_dir.name == "real"
    assert cache_fake.cache_dir.name == "fake"

    inp_hash = compute_hash("common prompt")
    cache_real.set("cand", inp_hash, {"val": "real_data"})
    cache_fake.set("cand", inp_hash, {"val": "fake_data", "raw_response": {"fake": True}})

    assert cache_real.get("cand", inp_hash)["val"] == "real_data"
    assert cache_fake.get("cand", inp_hash)["val"] == "fake_data"


def test_cache_refuses_fake_entry_on_set_in_real_mode(tmp_path):
    cache_real = BakeoffCache(tmp_path, mode="real")
    inp_hash = compute_hash("prompt")
    fake_data = {"text": "fake", "raw_response": {"fake": True}}

    with pytest.raises(FakeEntryInRealRunError, match="Refusing attempt to write fake data into real cache"):
        cache_real.set("cand", inp_hash, fake_data)


def test_cache_refuses_fake_entry_on_get_in_real_mode(tmp_path):
    cache_real = BakeoffCache(tmp_path, mode="real")
    inp_hash = compute_hash("prompt")

    # Manually inject a fake entry into internal cache (simulating an unpurged legacy file)
    key = f"real:cand:{inp_hash}"
    cache_real._cache[key] = {
        "mode": "fake",
        "candidate": "cand",
        "input_hash": inp_hash,
        "data": {"text": "mock", "raw_response": {"fake": True}},
    }

    with pytest.raises(FakeEntryInRealRunError, match="Refusing fake cache entry"):
        cache_real.get("cand", inp_hash)
