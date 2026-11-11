import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evals.bakeoff.metrics.wer import word_error_rate

cache_file = Path("evals/bakeoff/.cache/cache.json")
gt_file = Path("evals/corpus/ground_truth.json")

cache = json.load(open(cache_file, "r", encoding="utf-8"))
gt = json.load(open(gt_file, "r", encoding="utf-8"))

print(f"Total entries in cache: {len(cache)}")

# Count entries by candidate
candidate_counts = {}
for key, entry in cache.items():
    cand = entry.get("candidate", "unknown")
    candidate_counts[cand] = candidate_counts.get(cand, 0) + 1

print("Entries per candidate:")
for cand, count in candidate_counts.items():
    print(f"  - {cand}: {count}")

# Extract sample hypothesis vs reference pairs for groq_whisper and groq_whisper_prompted
print("\n--- Raw Hypothesis vs Reference Sample Pairs ---")
samples_unprompted = []
samples_prompted = []

for key, entry in cache.items():
    cand = entry.get("candidate")
    data = entry.get("data", {})
    hyp = data.get("text", "")
    rtt = data.get("rtt_ms", 0.0)
    # Check if raw_response has file info or groq id
    raw = data.get("raw_response", "")
    if cand == "groq_whisper" and len(samples_unprompted) < 5:
        samples_unprompted.append((hyp, rtt, raw))
    elif cand == "groq_whisper_prompted" and len(samples_prompted) < 8:
        samples_prompted.append((hyp, rtt, raw))

print("\n[groq_whisper (Unprompted Baseline)]")
for hyp, rtt, raw in samples_unprompted:
    print(f"  Hypothesis: '{hyp}' | RTT: {rtt} ms")

print("\n[groq_whisper_prompted (With Prompt Injection)]")
for hyp, rtt, raw in samples_prompted:
    print(f"  Hypothesis: '{hyp}' | RTT: {rtt} ms")

# WER Sanity Test Verification
print("\n--- WER Metric Sanity Checks ---")
test_cases = [
    ("Daimon is listening", "Daimon is listening", 0.0),
    ("Daimon is listening", "Daimon listening", 1/3),
    ("Daimon is listening", "Awaken Daimon is listening", 1/3),
    ("Daimon is listening", "completely wrong sentence here", 4/3),
]
for ref, hyp, expected in test_cases:
    computed = word_error_rate(ref, hyp)
    assert abs(computed - expected) < 1e-4, f"WER failed for ref='{ref}', hyp='{hyp}': got {computed}, expected {expected}"
    print(f"  PASS: ref='{ref}' vs hyp='{hyp}' -> WER={computed:.3f} (expected {expected:.3f})")

# Real vs Cached RTT comparison
real_rtts = [entry["data"]["rtt_ms"] for key, entry in cache.items() if "req_" in str(entry["data"].get("raw_response", ""))]
if real_rtts:
    import numpy as np
    print("\n--- Real API RTT vs Cached RTT ---")
    print(f"Real Groq API RTT: min={min(real_rtts):.1f} ms, median={np.median(real_rtts):.1f} ms, max={max(real_rtts):.1f} ms (p95={np.percentile(real_rtts, 95):.1f} ms)")
    print(f"Cached RTT (in-memory lookup): < 0.1 ms (instant cache hit)")
