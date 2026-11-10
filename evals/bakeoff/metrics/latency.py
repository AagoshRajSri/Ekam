"""
Latency aggregation and percentile calculation metrics.
"""

from __future__ import annotations

import math


def compute_percentiles(values: list[float]) -> dict[str, float]:
    """Compute summary percentiles (p50, p90, p95, p99, min, max, mean) from a list of latencies in ms."""
    if not values:
        return {
            "count": 0,
            "min": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "max": 0.0,
            "mean": 0.0,
        }

    s = sorted(values)
    n = len(s)

    def _pct(p: float) -> float:
        if n == 1:
            return s[0]
        k = (n - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return s[int(k)]
        d0 = s[int(f)] * (c - k)
        d1 = s[int(c)] * (k - f)
        return d0 + d1

    return {
        "count": n,
        "min": round(s[0], 1),
        "p50": round(_pct(50.0), 1),
        "p90": round(_pct(90.0), 1),
        "p95": round(_pct(95.0), 1),
        "p99": round(_pct(99.0), 1),
        "max": round(s[-1], 1),
        "mean": round(sum(s) / n, 1),
    }
