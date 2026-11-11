# Phase 1 Provider Bake-off Results

**Status:** REAL BENCHMARK (s01 recordings)  
**Date:** 2026-11-11  
**Hardware:** Windows x86_64, local CPU  
**Corpus Split:** dev (152 clips evaluated)  
**Dataset Label:** single-speaker baseline (speaker s01 only)  

> **Note on Method:** Aggregate performance metrics only. Raw per-clip logs and audio artifacts are stored in `evals/bakeoff/results/` (gitignored). Per AGENTS.md, **winners are NOT picked automatically** — the owner reviews the tables, inspects the audio samples, and selects candidates.

## 1. Speech-to-Text (STT) Candidates

| Candidate ID | Model | License | WER Overall | WER Q | WER D | WER N | Entity Acc | RTT p50 (ms) | RTT p95 (ms) |
|---|---|---|---|---|---|---|---|---|---|
| `groq_whisper` | whisper-large-v3-turbo | MIT (Whisper weights) / Proprietary API (Groq) | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 45 | 45 |
| `groq_whisper_prompted` | whisper-large-v3-turbo | MIT (Whisper weights) / Proprietary API (Groq) | 77.3% | 68.0% | 85.7% | 93.7% | 73.5% | 3469 | 12893 |

## 2. Fast LLM Candidates

Evaluated on fixed short prompts derived from Section C with Appendix A system prompt.

| Candidate ID | Model | License | TTFT p50 (ms) | TTFT p95 (ms) | Total p50 (ms) | Rule Compliance |
|---|---|---|---|---|---|---|

## 3. Text-to-Speech (TTS) Candidates

Audio samples containing the name are saved in `evals/bakeoff/results/tts_samples/` for owner listening.

| Candidate ID | Model / Voice | License | TTFB p50 (ms) | TTFB p95 (ms) | RTF (Real-Time Factor) | Quota Requests Used |
|---|---|---|---|---|---|---|

## 4. Name Capture & Alias Map Candidates (Section E)

Candidate spellings detected across Section E name clips. Informational only; the owner approves the final alias map.

| Candidate STT | Detected Spelling | Occurrences | Environments |
|---|---|---|---|
| `groq_whisper` | `Daimon.` | 48 | Q, D, N |
| `groq_whisper_prompted` | `Damon,` | 1 | Q, D, N |
| `groq_whisper_prompted` | `Daman, the human being, is a human being.` | 1 | Q, D, N |
| `groq_whisper_prompted` | `Daimon,` | 14 | Q, D, N |
| `groq_whisper_prompted` | `Daman,` | 1 | Q, D, N |
| `groq_whisper_prompted` | `Daimon.` | 15 | Q, D, N |
| `groq_whisper_prompted` | `David.` | 3 | Q, D, N |
| `groq_whisper_prompted` | `Daimon, helpful, and helpful.` | 3 | Q, D, N |
| `groq_whisper_prompted` | `Daimon here.` | 1 | Q, D, N |
| `groq_whisper_prompted` | `Demos.` | 1 | Q, D, N |
| `groq_whisper_prompted` | `Daimon, helpful.` | 1 | Q, D, N |
| `groq_whisper_prompted` | `Daimon, helpful, assistant, and a teacher.` | 1 | Q, D, N |
| `groq_whisper_prompted` | `Daimon, helpful assistant, natural spoken conversational English.` | 1 | Q, D, N |
| `groq_whisper_prompted` | `Diamond,` | 4 | Q, D, N |
| `groq_whisper_prompted` | `Diamond` | 1 | Q, D, N |

---
*Report generated automatically by `evals/bakeoff/run_bakeoff.py`. Aggregate numbers only.*
