# Phase 1 Provider Bake-off Results

**Status:** SYNTHETIC, not a benchmark  
**Date:** 2026-11-10  
**Hardware:** Windows x86_64, local CPU  
**Corpus Split:** dev (152 clips evaluated)  
**Dataset Label:** single-speaker baseline (speaker s01 only)  

> **Note on Method:** Aggregate performance metrics only. Raw per-clip logs and audio artifacts are stored in `evals/bakeoff/results/` (gitignored). Per AGENTS.md, **winners are NOT picked automatically** — the owner reviews the tables, inspects the audio samples, and selects candidates.

> [!WARNING]
> **Synthetic Data Only:** The numbers below were generated using synthetic/fake offline adapters because master recordings for the corpus have not yet been recorded. **Do not use these numbers for production decisions.** Re-run this harness once real corpus WAVs exist.

## 1. Speech-to-Text (STT) Candidates

| Candidate ID | Model | License | WER Overall | WER Q | WER D | WER N | Entity Acc | RTT p50 (ms) | RTT p95 (ms) |
|---|---|---|---|---|---|---|---|---|---|
| `groq_whisper` | whisper-large-v3-turbo | MIT (Whisper weights) / Proprietary API (Groq) | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 45 | 45 |

## 2. Fast LLM Candidates

Evaluated on fixed short prompts derived from Section C with Appendix A system prompt.

| Candidate ID | Model | License | TTFT p50 (ms) | TTFT p95 (ms) | Total p50 (ms) | Rule Compliance |
|---|---|---|---|---|---|---|
| `groq_qwen` | qwen/qwen3.8-27b | Apache-2.0 (Qwen weights) / Proprietary API (Groq) | 120 | 120 | 210 | 100.0% |
| `gemini_flash` | gemini-3.8-flash | Proprietary API (Google AI Studio) | 120 | 120 | 210 | 100.0% |
| `ollama_qwen` | qwen2.5:7b | Apache-2.0 (Qwen weights) / MIT (Ollama runtime) | 120 | 120 | 210 | 100.0% |

## 3. Text-to-Speech (TTS) Candidates

Audio samples containing the name are saved in `evals/bakeoff/results/tts_samples/` for owner listening.

| Candidate ID | Model / Voice | License | TTFB p50 (ms) | TTFB p95 (ms) | RTF (Real-Time Factor) | Quota Requests Used |
|---|---|---|---|---|---|---|
| `groq_orpheus` | canopylabs/orpheus-v1-english | Proprietary API (Groq / Canopy Labs) | 95 | 95 | 0.100 | 0 |
| `piper_lessac` | en_US-lessac-medium | GPL-3.0 (piper-tts runtime). Voice model: verify MODEL_CARD before distribution. | 95 | 95 | 0.100 | 0 |
| `kokoro` | kokoro-v1_0.pth | Apache-2.0 (permissive) | 95 | 95 | 0.100 | 0 |

## 4. Name Capture & Alias Map Candidates (Section E)

Candidate spellings detected across Section E name clips. Informational only; the owner approves the final alias map.

| Candidate STT | Detected Spelling | Occurrences | Environments |
|---|---|---|---|
| `groq_whisper` | `Daimon.` | 48 | Q, D, N |

---
*Report generated automatically by `evals/bakeoff/run_bakeoff.py`. Aggregate numbers only.*
