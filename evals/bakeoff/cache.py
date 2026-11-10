"""
Resumable evaluation cache keyed by (candidate_id, input_hash).
Avoids re-running expensive API or synthesis requests.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


def compute_hash(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


class BakeoffCache:
    def __init__(self, cache_dir: Path | str) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "cache.json"
        self._cache: dict[str, Any] = {}
        self._load()

    def _make_key(self, candidate_id: str, input_hash: str) -> str:
        return f"{candidate_id}:{input_hash}"

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

    def get(self, candidate_id: str, input_hash: str) -> Any | None:
        key = self._make_key(candidate_id, input_hash)
        entry = self._cache.get(key)
        if entry:
            return entry.get("data")
        return None

    def set(self, candidate_id: str, input_hash: str, data: Any) -> None:
        key = self._make_key(candidate_id, input_hash)
        self._cache[key] = {
            "candidate": candidate_id,
            "input_hash": input_hash,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data": data,
        }
        self._save()

    def count(self) -> int:
        return len(self._cache)
