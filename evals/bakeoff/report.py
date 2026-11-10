"""
Markdown report generator for the Phase 1 Provider Bake-off.
Produces aggregate tables only. Raw per-clip results are saved to results/ (gitignored).
Winners are NOT picked automatically.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def generate_markdown_report(
    stt_results: dict[str, Any],
    llm_results: dict[str, Any],
    tts_results: dict[str, Any],
    alias_candidates: dict[str, Any],
    output_path: Path,
    is_synthetic: bool = True,
    split_used: str = "dev",
    total_clips: int = 0,
) -> str:
    date_str = time.strftime("%Y-%m-%d", time.gmtime())
    status_label = "SYNTHETIC, not a benchmark" if is_synthetic else "REAL BENCHMARK (s01 recordings)"

    lines = [
        "# Phase 1 Provider Bake-off Results",
        "",
        f"**Status:** {status_label}  ",
        f"**Date:** {date_str}  ",
        "**Hardware:** Windows x86_64, local CPU  ",
        f"**Corpus Split:** {split_used} ({total_clips} clips evaluated)  ",
        "**Dataset Label:** single-speaker baseline (speaker s01 only)  ",
        "",
        "> **Note on Method:** Aggregate performance metrics only. Raw per-clip logs and audio artifacts are stored in `evals/bakeoff/results/` (gitignored). Per AGENTS.md, **winners are NOT picked automatically** — the owner reviews the tables, inspects the audio samples, and selects candidates.",
        "",
    ]

    if is_synthetic:
        lines.extend([
            "> [!WARNING]",
            "> **Synthetic Data Only:** The numbers below were generated using synthetic/fake offline adapters because master recordings for the corpus have not yet been recorded. **Do not use these numbers for production decisions.** Re-run this harness once real corpus WAVs exist.",
            "",
        ])

    # ── 1. Speech-to-Text (STT) ──────────────────────────────────────────────
    lines.extend([
        "## 1. Speech-to-Text (STT) Candidates",
        "",
        "| Candidate ID | Model | License | WER Overall | WER Q | WER D | WER N | Entity Acc | RTT p50 (ms) | RTT p95 (ms) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])

    for cid, data in stt_results.items():
        model = data.get("model", "—")
        license_str = data.get("license", "—")
        wer_all = f"{data.get('wer_overall', 0.0) * 100:.1f}%"
        wer_q = f"{data.get('wer_q', 0.0) * 100:.1f}%"
        wer_d = f"{data.get('wer_d', 0.0) * 100:.1f}%"
        wer_n = f"{data.get('wer_n', 0.0) * 100:.1f}%"
        ent_acc = f"{data.get('entity_accuracy', 0.0) * 100:.1f}%"
        rtt_p50 = f"{data.get('rtt_p50', 0.0):.0f}"
        rtt_p95 = f"{data.get('rtt_p95', 0.0):.0f}"
        lines.append(f"| `{cid}` | {model} | {license_str} | {wer_all} | {wer_q} | {wer_d} | {wer_n} | {ent_acc} | {rtt_p50} | {rtt_p95} |")

    lines.append("")

    # ── 2. Fast LLM Candidates ───────────────────────────────────────────────
    lines.extend([
        "## 2. Fast LLM Candidates",
        "",
        "Evaluated on fixed short prompts derived from Section C with Appendix A system prompt.",
        "",
        "| Candidate ID | Model | License | TTFT p50 (ms) | TTFT p95 (ms) | Total p50 (ms) | Rule Compliance |",
        "|---|---|---|---|---|---|---|",
    ])

    for cid, data in llm_results.items():
        model = data.get("model", "—")
        license_str = data.get("license", "—")
        ttft_p50 = f"{data.get('ttft_p50', 0.0):.0f}"
        ttft_p95 = f"{data.get('ttft_p95', 0.0):.0f}"
        tot_p50 = f"{data.get('total_p50', 0.0):.0f}"
        comp = f"{data.get('compliance_pct', 0.0):.1f}%"
        lines.append(f"| `{cid}` | {model} | {license_str} | {ttft_p50} | {ttft_p95} | {tot_p50} | {comp} |")

    lines.append("")

    # ── 3. Text-to-Speech (TTS) Candidates ───────────────────────────────────
    lines.extend([
        "## 3. Text-to-Speech (TTS) Candidates",
        "",
        "Audio samples containing the name are saved in `evals/bakeoff/results/tts_samples/` for owner listening.",
        "",
        "| Candidate ID | Model / Voice | License | TTFB p50 (ms) | TTFB p95 (ms) | RTF (Real-Time Factor) | Quota Requests Used |",
        "|---|---|---|---|---|---|---|",
    ])

    for cid, data in tts_results.items():
        model = data.get("model", "—")
        license_str = data.get("license", "—")
        ttfb_p50 = f"{data.get('ttfb_p50', 0.0):.0f}"
        ttfb_p95 = f"{data.get('ttfb_p95', 0.0):.0f}"
        rtf = f"{data.get('rtf_p50', 0.0):.3f}"
        quota = f"{data.get('quota_used', 0)}"
        lines.append(f"| `{cid}` | {model} | {license_str} | {ttfb_p50} | {ttfb_p95} | {rtf} | {quota} |")

    lines.append("")

    # ── 4. Section E: Name Alias Candidates ──────────────────────────────────
    lines.extend([
        "## 4. Name Capture & Alias Map Candidates (Section E)",
        "",
        "Candidate spellings detected across Section E name clips. Informational only; the owner approves the final alias map.",
        "",
        "| Candidate STT | Detected Spelling | Occurrences | Environments |",
        "|---|---|---|---|",
    ])

    if alias_candidates:
        for cid, variants in alias_candidates.items():
            for spelling, count in variants.items():
                lines.append(f"| `{cid}` | `{spelling}` | {count} | Q, D, N |")
    else:
        lines.append("| (pending real recordings) | — | — | — |")

    lines.append("")
    lines.extend([
        "---",
        "*Report generated automatically by `evals/bakeoff/run_bakeoff.py`. Aggregate numbers only.*",
    ])

    report_text = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return report_text
