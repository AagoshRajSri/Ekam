"""
Resumable evaluation cache keyed by (mode, candidate_id, input_hash).
Maintains strict provenance: separate storage directories for real vs. fake runs,
refuses fake cache entries in real benchmark runs, and tags every entry with explicit mode.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Literal

CacheMode = Literal["real", "fake"]


def compute_hash(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


class FakeEntryInRealRunError(RuntimeError):
    """Raised when a fake/mock entry is encountered or requested during a real benchmark run."""
    pass


class BakeoffCache:
    def __init__(self, cache_dir: Path | str, mode: CacheMode = "real") -> None:
        self.mode: CacheMode = mode
        base_dir = Path(cache_dir)
        # Ensure separate directories for real vs. fake
        if base_dir.name in ("real", "fake"):
            self.cache_dir = base_dir
        else:
            self.cache_dir = base_dir / mode

        self.cache_file = self.cache_dir / "cache.json"
        self._cache: dict[str, Any] = {}
        self._load()

    def _make_key(self, candidate_id: str, input_hash: str) -> str:
        return f"{self.mode}:{candidate_id}:{input_hash}"

    def _load(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}
        else:
            self._cache = {}

    def _save(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = self.cache_file.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2)
        tmp_file.replace(self.cache_file)

    def get(self, candidate_id: str, input_hash: str, enforce_real: bool | None = None) -> Any | None:
        key = self._make_key(candidate_id, input_hash)
        entry = self._cache.get(key)

        # Fallback check for legacy keys without mode prefix
        if not entry:
            legacy_key = f"{candidate_id}:{input_hash}"
            entry = self._cache.get(legacy_key)

        if not entry:
            return None

        entry_mode = entry.get("mode")
        raw_resp = entry.get("data", {}).get("raw_response") if isinstance(entry.get("data"), dict) else None
        is_entry_fake = (
            entry_mode == "fake"
            or (isinstance(raw_resp, dict) and raw_resp.get("fake") is True)
            or (isinstance(entry.get("data"), dict) and entry.get("data", {}).get("fake") is True)
            or (isinstance(entry.get("data"), dict) and entry.get("data", {}).get("rtt_ms") == 45.0 and candidate_id.startswith("groq_whisper"))
        )

        should_enforce = (self.mode == "real") if enforce_real is None else enforce_real
        if should_enforce and is_entry_fake:
            raise FakeEntryInRealRunError(
                f"FATAL: Refusing fake cache entry for '{candidate_id}' in real mode! (key: {key})"
            )

        return entry.get("data")

    def set(self, candidate_id: str, input_hash: str, data: Any) -> None:
        raw_resp = data.get("raw_response") if isinstance(data, dict) else None
        is_data_fake = (
            self.mode == "fake"
            or (isinstance(raw_resp, dict) and raw_resp.get("fake") is True)
            or (isinstance(data, dict) and data.get("fake") is True)
        )

        if self.mode == "real" and is_data_fake:
            raise FakeEntryInRealRunError(
                f"FATAL: Refusing attempt to write fake data into real cache for '{candidate_id}'!"
            )

        key = self._make_key(candidate_id, input_hash)
        self._cache[key] = {
            "mode": self.mode,
            "candidate": candidate_id,
            "input_hash": input_hash,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data": data,
        }
        self._save()

    def count(self) -> int:
        return len(self._cache)
