"""
assign_split.py: Deterministic seeded split assignment for the Daimon benchmark corpus.
Assigns BY ITEM (both takes of an item in the same split), stratified by section and env.
Writes ground_truth.json and evals/corpus/split.lock.
Refuses to re-assign if split.lock records result_runs > 0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path


def compute_sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def get_clip_type(section: str, item_id: str, expected_action: str) -> str:
    if section == "A":
        return "session_wake"
    elif section == "C":
        return "addressed_command"
    elif section == "E":
        return "name_capture"
    elif section == "G":
        return "sidetalk_negative"
    elif section == "I":
        if expected_action == "route_to_llm":
            return "hindi_addressed"
        return "hindi_unaddressed"
    return "unknown"


def assign_split(
    manifest_path: Path,
    ground_truth_path: Path,
    lock_path: Path,
    seed: int = 42,
    dev_ratio: float = 0.6,
    force: bool = False,
) -> int:
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    # Check lock file
    if lock_path.exists() and not force:
        try:
            with open(lock_path, "r", encoding="utf-8") as lf:
                lock_data = json.load(lf)
            result_runs = lock_data.get("result_runs", 0)
            if result_runs > 0:
                print(
                    f"REFUSING TO RE-ASSIGN SPLIT: split.lock records {result_runs} test split result run(s).",
                    file=sys.stderr,
                )
                print("Re-assigning the split after test runs invalidates benchmark integrity.", file=sys.stderr)
                return 1
            else:
                print("Note: split.lock exists with result_runs=0. Proceeding with deterministic split generation.")
        except Exception as e:
            print(f"Warning: Could not read existing split.lock: {e}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_raw = f.read()
    manifest = json.loads(manifest_raw)
    manifest_hash = compute_sha256(manifest_raw)

    items = manifest.get("items", [])
    clips = manifest.get("clips", [])

    # Group items by stratum: (section, env)
    strata: dict[tuple[str, str], list[dict]] = {}
    for item in items:
        key = (item["section"], item["env"])
        strata.setdefault(key, []).append(item)

    rng = random.Random(seed)
    item_split: dict[str, str] = {}

    for (sec, env), stratum_items in sorted(strata.items()):
        # Sort items deterministically by ID before shuffling with seeded RNG
        sorted_items = sorted(stratum_items, key=lambda x: x["id"])
        indices = list(range(len(sorted_items)))
        rng.shuffle(indices)

        n_dev = int(round(len(sorted_items) * dev_ratio))
        # Ensure at least 1 dev and 1 test if len >= 2
        if len(sorted_items) >= 2:
            n_dev = max(1, min(len(sorted_items) - 1, n_dev))

        dev_indices = set(indices[:n_dev])
        for idx, it in enumerate(sorted_items):
            item_split[it["id"]] = "dev" if idx in dev_indices else "test"

    # Build ground_truth.json dictionary mapping filename -> clip ground truth
    ground_truth: dict[str, dict] = {}
    for clip in clips:
        item_id = clip["id"]
        split = item_split[item_id]
        fname = clip["filename"]
        action = clip["expected_action"]
        status = clip["policy_status"]

        entry = {
            "id": item_id,
            "section": clip["section"],
            "text": clip["text"],
            "speaker_id": clip.get("speaker", "s01"),
            "environment": clip["env"],
            "take": clip["take"],
            "split": split,
            "expected_action": action,
            "policy_status": status,
            "type": get_clip_type(clip["section"], item_id, action),
            "entities": clip.get("entities", []),
            "quality_flag": "ok",
        }
        if status == "open":
            entry["open_policy_note"] = "Open policy item; reported separately and never counts toward pass/fail."
        if clip["section"] == "E":
            entry["stt_output"] = None

        ground_truth[fname] = entry

    gt_json = json.dumps(ground_truth, indent=2, ensure_ascii=False)
    ground_truth_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ground_truth_path, "w", encoding="utf-8") as f:
        f.write(gt_json)

    # Compute assignment hash
    assignment_hash = compute_sha256(json.dumps(item_split, sort_keys=True))

    dev_item_count = sum(1 for s in item_split.values() if s == "dev")
    test_item_count = sum(1 for s in item_split.values() if s == "test")
    dev_clip_count = sum(1 for c in ground_truth.values() if c["split"] == "dev")
    test_clip_count = sum(1 for c in ground_truth.values() if c["split"] == "test")

    lock_data = {
        "assignment_hash": assignment_hash,
        "manifest_hash": manifest_hash,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": seed,
        "dev_ratio": dev_ratio,
        "total_items": len(items),
        "dev_items": dev_item_count,
        "test_items": test_item_count,
        "total_clips": len(ground_truth),
        "dev_clips": dev_clip_count,
        "test_clips": test_clip_count,
        "result_runs": 0,
        "note": "Dev/test split is locked. result_runs will increment when --final (test split) runs. Split changes are rejected if result_runs > 0.",
    }

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w", encoding="utf-8") as lf:
        json.dump(lock_data, lf, indent=2)

    print(f"Ground truth written to: {ground_truth_path}")
    print(f"Split lock written to:   {lock_path}")
    print(f"Items: Total {len(items)}, Dev {dev_item_count} ({dev_item_count/len(items)*100:.1f}%), Test {test_item_count} ({test_item_count/len(items)*100:.1f}%)")
    print(f"Clips: Total {len(ground_truth)}, Dev {dev_clip_count} ({dev_clip_count/len(ground_truth)*100:.1f}%), Test {test_clip_count} ({test_clip_count/len(ground_truth)*100:.1f}%)")
    print("\nStrata Breakdown (Items):")
    for (sec, env), stratum_items in sorted(strata.items()):
        dev_in_s = sum(1 for it in stratum_items if item_split[it["id"]] == "dev")
        test_in_s = sum(1 for it in stratum_items if item_split[it["id"]] == "test")
        print(f"  Section {sec} [{env}]: {dev_in_s:2d} dev / {test_in_s:2d} test (total {len(stratum_items)})")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic seeded dev/test split assigner.")
    parser.add_argument("--manifest", default="evals/corpus/manifest.json", help="Path to manifest.json")
    parser.add_argument("--ground-truth", default="evals/corpus/ground_truth.json", help="Path to ground_truth.json")
    parser.add_argument("--lock", default="evals/corpus/split.lock", help="Path to split.lock")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for deterministic split")
    parser.add_argument("--dev-ratio", type=float, default=0.6, help="Target ratio for dev split (default: 0.6)")
    parser.add_argument("--force", action="store_true", help="Force split regeneration even if lock exists")

    args = parser.parse_args()
    return assign_split(
        manifest_path=Path(args.manifest),
        ground_truth_path=Path(args.ground_truth),
        lock_path=Path(args.lock),
        seed=args.seed,
        dev_ratio=args.dev_ratio,
        force=args.force,
    )


if __name__ == "__main__":
    sys.exit(main())
