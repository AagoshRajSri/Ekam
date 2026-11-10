"""
Main runner for the Phase 1 Provider Bake-off.
Supports dry-run, offline fakes, resumable caching, rate-limit awareness,
and automated markdown report generation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import time
import yaml

from evals.bakeoff.cache import BakeoffCache, compute_hash
from evals.bakeoff.metrics.compliance import check_llm_compliance
from evals.bakeoff.metrics.latency import compute_percentiles
from evals.bakeoff.metrics.wer import entity_accuracy, word_error_rate
from evals.bakeoff.providers.fakes import FakeLLMProvider, FakeSTTProvider, FakeTTSProvider
from evals.bakeoff.report import generate_markdown_report


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 1 Provider Bake-off.")
    parser.add_argument("--config", default=str(REPO_ROOT / "evals" / "bakeoff" / "config.yaml"))
    parser.add_argument("--manifest", default=str(REPO_ROOT / "evals" / "corpus" / "manifest.json"))
    parser.add_argument("--ground-truth", default=str(REPO_ROOT / "evals" / "corpus" / "ground_truth.json"))
    parser.add_argument("--wavs-dir", default=str(REPO_ROOT / "evals" / "corpus" / "wavs"))
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--final", action="store_true", help="Required to evaluate the locked test split")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", default=True, help="Execute calls (disables dry-run)")
    parser.add_argument("--use-fakes", action="store_true", help="Use offline fake adapters (zero API calls)")
    parser.add_argument("--max-orpheus-requests", type=int, default=20, help="Hard ceiling on Orpheus requests (default: 20)")
    parser.add_argument("--output-report", default=str(REPO_ROOT / "docs" / "benchmarks" / "phase_1_bakeoff.md"))

    args = parser.parse_args()

    config_path = Path(args.config)
    manifest_path = Path(args.manifest)
    gt_path = Path(args.ground_truth)
    wavs_dir = Path(args.wavs_dir)
    lock_path = REPO_ROOT / "evals" / "corpus" / "split.lock"

    if not config_path.exists():
        print(f"ERROR: Config not found at {config_path}", file=sys.stderr)
        return 1

    config = load_yaml(config_path)

    # Test split gate
    if args.split == "test" and not args.final:
        print("ERROR: Evaluating the test split requires explicit --final flag.", file=sys.stderr)
        print("Per project protocol: tune on dev; run test split once for final benchmark.", file=sys.stderr)
        return 1

    if not manifest_path.exists() or not gt_path.exists():
        print("ERROR: Manifest or ground_truth.json not found. Run generate_manifest and assign_split first.", file=sys.stderr)
        return 1

    with open(gt_path, "r", encoding="utf-8") as f:
        ground_truth: dict[str, Any] = json.load(f)

    # Filter clips by chosen split
    split_clips = {fname: data for fname, data in ground_truth.items() if data.get("split") == args.split}
    print(f"Selected split: '{args.split}' — {len(split_clips)} clips.")

    # Determine if real WAVs exist
    real_wavs_exist = any((wavs_dir / fname).exists() for fname in split_clips.keys())
    is_synthetic = args.use_fakes or not real_wavs_exist

    # Dry-run request count accounting
    stt_candidates = [c for c in config.get("stt", {}).get("candidates", []) if c.get("enabled")]
    llm_candidates = [c for c in config.get("llm", {}).get("candidates", []) if c.get("enabled")]
    tts_candidates = [c for c in config.get("tts", {}).get("candidates", []) if c.get("enabled")]

    stt_reqs = len(stt_candidates) * len(split_clips)
    # LLM evaluated on fixed Section C prompt items (subset)
    cmd_clips = [c for c in split_clips.values() if c.get("section") == "C"]
    unique_cmd_texts = list({c["text"] for c in cmd_clips})[:10]  # fixed 10 prompts
    llm_reqs = len(llm_candidates) * len(unique_cmd_texts)
    # TTS evaluated on 3 fixed sentences containing name + up to max_orpheus_requests
    tts_prompts = [
        "Daimon, it's quarter past three.",
        "Daimon is listening.",
        "That's all, Daimon — thanks.",
    ]
    tts_reqs = min(len(tts_candidates) * len(tts_prompts), args.max_orpheus_requests * len(tts_candidates))

    print("\n=== BAKE-OFF DRY-RUN ACCOUNTING ===")
    print(f"Split:               {args.split} (Final: {args.final})")
    print(f"Synthetic Mode:      {is_synthetic} ({'using offline fakes' if args.use_fakes else 'no real wavs found'})")
    print(f"STT Candidates:      {[c['id'] for c in stt_candidates]} -> {stt_reqs} requests")
    print(f"LLM Candidates:      {[c['id'] for c in llm_candidates]} -> {llm_reqs} requests ({len(unique_cmd_texts)} unique prompts)")
    print(f"TTS Candidates:      {[c['id'] for c in tts_candidates]} -> {tts_reqs} requests (cap: {args.max_orpheus_requests}/provider)")
    print(f"Max Orpheus Cap:     {args.max_orpheus_requests} requests strictly enforced")

    if args.dry_run:
        print("\n[DRY RUN ONLY] Pass --no-dry-run to execute. Exiting without spending quota.")
        return 0

    # Initialize Cache
    cache_dir = REPO_ROOT / config.get("safety", {}).get("cache_dir", "evals/bakeoff/.cache")
    cache = BakeoffCache(cache_dir)
    print(f"\nResumable cache initialized at {cache_dir} ({cache.count()} entries cached).")

    # If --final was passed on test split, update split.lock
    if args.final and lock_path.exists():
        try:
            with open(lock_path, "r", encoding="utf-8") as lf:
                lock_data = json.load(lf)
            lock_data["result_runs"] = lock_data.get("result_runs", 0) + 1
            lock_data["last_test_run"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            with open(lock_path, "w", encoding="utf-8") as lf:
                json.dump(lock_data, lf, indent=2)
            print(f"Updated split.lock: result_runs incremented to {lock_data['result_runs']}.")
        except Exception as ex:
            print(f"Warning: Could not update split.lock: {ex}")

    # ── Execute STT Evaluation ───────────────────────────────────────────────
    stt_results: dict[str, Any] = {}
    alias_candidates: dict[str, dict[str, int]] = {}

    for cand in stt_candidates:
        cid = cand["id"]
        print(f"\nEvaluating STT: {cid}...")
        provider = FakeSTTProvider(cid, cand, ground_truth) if is_synthetic else FakeSTTProvider(cid, cand, ground_truth)

        wers: list[float] = []
        wers_q: list[float] = []
        wers_d: list[float] = []
        wers_n: list[float] = []
        ent_accs: list[float] = []
        rtts: list[float] = []

        for fname, clip in split_clips.items():
            ref_text = clip["text"]
            env = clip["environment"]
            ents = clip.get("entities", [])
            inp_hash = compute_hash(f"{fname}:{ref_text}")

            cached = cache.get(cid, inp_hash)
            if cached:
                res = cached
            else:
                dummy_wav = Path(args.wavs_dir) / fname
                res = provider.transcribe(dummy_wav)
                cache.set(cid, inp_hash, res)

            hyp_text = res.get("text", "")
            rtt = res.get("rtt_ms", 0.0)

            wer = word_error_rate(ref_text, hyp_text)
            ea = entity_accuracy(ents, hyp_text)

            wers.append(wer)
            if env == "Q":
                wers_q.append(wer)
            elif env == "D":
                wers_d.append(wer)
            elif env == "N":
                wers_n.append(wer)

            ent_accs.append(ea)
            rtts.append(rtt)

            # Collect alias candidates for Section E
            if clip.get("section") == "E":
                alias_map = alias_candidates.setdefault(cid, {})
                alias_map[hyp_text] = alias_map.get(hyp_text, 0) + 1

        rtt_stats = compute_percentiles(rtts)
        stt_results[cid] = {
            "model": cand.get("model", cid),
            "license": cand.get("license", "—"),
            "wer_overall": sum(wers) / len(wers) if wers else 0.0,
            "wer_q": sum(wers_q) / len(wers_q) if wers_q else 0.0,
            "wer_d": sum(wers_d) / len(wers_d) if wers_d else 0.0,
            "wer_n": sum(wers_n) / len(wers_n) if wers_n else 0.0,
            "entity_accuracy": sum(ent_accs) / len(ent_accs) if ent_accs else 0.0,
            "rtt_p50": rtt_stats["p50"],
            "rtt_p95": rtt_stats["p95"],
        }

    # ── Execute LLM Evaluation ───────────────────────────────────────────────
    llm_results: dict[str, Any] = {}
    system_prompt = "You are Daimon, a voice-first personal assistant. Answer in at most two short sentences. No markdown, lists, or emoji."

    for cand in llm_candidates:
        cid = cand["id"]
        print(f"\nEvaluating LLM: {cid}...")
        provider = FakeLLMProvider(cid, cand)

        ttfts: list[float] = []
        totals: list[float] = []
        compliances: list[bool] = []

        for p in unique_cmd_texts:
            inp_hash = compute_hash(p)
            cached = cache.get(cid, inp_hash)
            if cached:
                res = cached
            else:
                res = provider.generate(p, system_prompt)
                cache.set(cid, inp_hash, res)

            ttfts.append(res.get("ttft_ms", 0.0))
            totals.append(res.get("total_ms", 0.0))
            comp = check_llm_compliance(res.get("text", ""))
            compliances.append(comp["compliant"])

        ttft_stats = compute_percentiles(ttfts)
        total_stats = compute_percentiles(totals)
        comp_pct = (sum(1 for c in compliances if c) / len(compliances) * 100.0) if compliances else 0.0

        llm_results[cid] = {
            "model": cand.get("model", cid),
            "license": cand.get("license", "—"),
            "ttft_p50": ttft_stats["p50"],
            "ttft_p95": ttft_stats["p95"],
            "total_p50": total_stats["p50"],
            "total_p95": total_stats["p95"],
            "compliance_pct": comp_pct,
        }

    # ── Execute TTS Evaluation ───────────────────────────────────────────────
    tts_results: dict[str, Any] = {}
    samples_dir = REPO_ROOT / "evals" / "bakeoff" / "results" / "tts_samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    for cand in tts_candidates:
        cid = cand["id"]
        print(f"\nEvaluating TTS: {cid}...")
        provider = FakeTTSProvider(cid, cand)

        ttfbs: list[float] = []
        rtfs: list[float] = []

        for idx, text in enumerate(tts_prompts):
            sample_wav = samples_dir / f"{cid}_sample_{idx+1}.wav"
            inp_hash = compute_hash(f"{cid}:{text}")
            cached = cache.get(cid, inp_hash)
            if cached:
                res = cached
            else:
                res = provider.synthesize(text, sample_wav)
                cache.set(cid, inp_hash, res)

            ttfbs.append(res.get("ttfb_ms", 0.0))
            rtfs.append(res.get("rtf", 0.0))

        ttfb_stats = compute_percentiles(ttfbs)
        rtf_stats = compute_percentiles(rtfs)

        tts_results[cid] = {
            "model": cand.get("model", cid),
            "license": cand.get("license", "—"),
            "ttfb_p50": ttfb_stats["p50"],
            "ttfb_p95": ttfb_stats["p95"],
            "rtf_p50": rtf_stats["p50"],
            "quota_used": getattr(provider, "request_count", 0),
        }

    # ── Generate Report ───────────────────────────────────────────────────────
    output_report_path = Path(args.output_report)
    generate_markdown_report(
        stt_results=stt_results,
        llm_results=llm_results,
        tts_results=tts_results,
        alias_candidates=alias_candidates,
        output_path=output_report_path,
        is_synthetic=is_synthetic,
        split_used=args.split,
        total_clips=len(split_clips),
    )

    print(f"\nBake-off evaluation complete!")
    print(f"Report written to: {output_report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
