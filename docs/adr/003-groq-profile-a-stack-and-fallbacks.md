# ADR-003: Groq Pipeline as Profile A Deviation, Model Pinning, Rate Limits, and Fallback Architecture

**Status:** Accepted  
**Date:** 2026-11-07  
**Author:** Ekam Core Team  
**Scope:** Phase 0–1 Voice Pipeline & Failover Architecture  

---

## Context

The base Profile A specification in `BABY_FREE_TO_PREMIUM.md` originally anticipated:
- **STT:** LiveKit Inference credits or local `faster-whisper`
- **LLM:** Groq Llama 3.3 70B → Gemini Flash → local Ollama Qwen
- **TTS:** Local Piper or Kokoro

During Phase 0 smoke testing:
1. `llama-3.3-70b-versatile` returned `404 - model not found or no access` on standard free-tier Groq API keys.
2. Groq's model catalog exposes `qwen/qwen3.8-27b` with ultra-low latency (~129–181 ms TTFT).
3. Groq also hosts a cloud TTS endpoint (`canopylabs/orpheus-v1-english`, voice `autumn`) with ~194–338 ms TTFB, useful for high-quality demos and benchmarks.
4. Groq Whisper (`whisper-large-v3-turbo`) delivers fast utterance-based STT with ~0.8s transcript latency. Note: Whisper is utterance-based (processes finalized audio buffers after VAD turn commit), whereas LLM generation and Orpheus TTS stream chunks.
5. Live test run: The initial 7-turn conversation was an initial **smoke test** verifying plumbing, VAD, and model compatibility. It is **not** an empirical benchmark baseline (benchmarks require the standardized corpus from `evals/corpus/`).

This ADR formalizes adopting Groq for STT, LLM, and demo/benchmark TTS as an authorized Profile A deviation, pins model identifiers, defines provider abstractions, establishes strict rate-limit guardrails, and specifies fallback chains.

---

## Decision

### 1. Pinned Model Identifiers (Exact Provider IDs)

Exact model IDs retrieved from provider catalog APIs:

| Pipeline Layer | Provider | Exact Pinned Model ID / Voice | Mode | Notes |
|---|---|---|---|---|
| **STT (Primary)** | Groq | `whisper-large-v3-turbo` | Utterance-based | `language="en"`, 16 kHz mono |
| **STT (Fallback)** | Local | `faster-whisper` (base.en / small.en) | Utterance-based | Zero network dependency |
| **Fast LLM (Primary)**| Groq | `qwen/qwen3.8-27b` | Streaming | `temperature=0.4`, `max_tokens=120`, thinking OFF |
| **Fast LLM (Secondary)**| Google | `gemini-3.8-flash` | Streaming | Failover for Groq 429/5xx (verified via AI Studio API) |
| **LLM (Tertiary)** | Local | `ollama/qwen2.5:7b` | Streaming | Local CPU/GPU fallback |
| **TTS (Demos/Bake-off)**| Groq | `canopylabs/orpheus-v1-english` (voice: `autumn`) | Chunked Stream | Strictly capped: 100 req/hour limit |
| **TTS (Dev & Tests)** | Local | Piper (GPL-3.0, dev/fallback-only) / Kokoro (Apache-2.0) | Local Stream | Default for all automated tests & dev |
| **VAD** | Local | Silero VAD (ONNX, CPU, 16 kHz) | In-process | < 1 ms |
| **Turn Detection** | LiveKit | `turn-detector-v1` (multilingual) | In-process/Cloud | ~400 ms endpointing |

### 2. Provider Abstractions (Behind Interfaces)

Per Spec §12 and `AGENTS.md`, no model or provider is hard-coded into business logic:
- **STT Interface:** Implements LiveKit `stt.STT` protocol.
- **LLM Interface:** Implements LiveKit `llm.LLM` protocol with automatic fallback chaining.
- **TTS Interface:** Implements LiveKit `tts.TTS` chunked stream protocol.

### 3. Rate Limits & TTS Dev Isolation

Empirical rate limits observed on Groq free-tier:
- **Groq Chat / LLM:** 1,000 requests per rolling window, 8,000 tokens/min.
- **Groq Orpheus TTS:** **100 requests per rolling hour**, 1,200 tokens/min.

**Isolation Rules:**
1. **Dev & Automated Tests:** Groq Orpheus MUST NOT be invoked during automated test runs (such as the barge-in test suite) or general dev looping. Development defaults to local TTS (Piper/Kokoro) to conserve the 100 req/hour quota.
2. **Quota Tracking:** An in-memory, rolling per-hour counter tracks TTS requests.
3. **429 Recovery Line & Quota Resilience:**
   - Must NOT use Orpheus to synthesize (Orpheus itself may be 429'd).
   - Delivered via a pre-recorded WAV (`assets/recovery_429.wav`, 24 kHz mono 16-bit, synthesized with local Piper):
     > *"I've hit my voice limit, switching to my backup voice."*
   - Once the recovery line is emitted, ongoing speech continues via local Piper TTS.
   - **Proactive Headroom Switch:** When rolling hourly headroom drops to $\le 10\%$ of limit ($\le 10$ remaining of 100), `GuardedOrpheusTTS` switches proactively to Piper before hitting hard server rejection.
   - **Retry-After & Cooldown:** On any server-side 429 or 5xx, the `Retry-After` header is honored (or an exponential backoff starting at 60 s up to 3600 s is engaged).
   - **Persistence Across Restarts:** Rolling request timestamps are persisted to local `tts_quota_timestamps.jsonl` (gitignored), preventing quota evasion or inadvertent exhaustion on process restarts.
   - **Auto-Return:** When the cooldown expires and the rolling 1-hour window drops below the limit, Orpheus automatically resumes as the primary TTS engine.
   - Concurrently emits status and transcript to the client UI via the `telemetry` data channel.

### 4. Local TTS Licensing & Distribution Constraints (Piper vs. Kokoro)

- **Piper Licensing:** `piper-tts` is licensed under **GPL-3.0** due to embedded `espeak-ng` code and runtime dependencies. Individual voice ONNX models carry distinct licenses that **must be verified before any distribution**. Check the specific model's `MODEL_CARD.md` on the [rhasspy/piper-voices HuggingFace repo](https://huggingface.co/rhasspy/piper-voices) — do not assume any particular voice is public domain or ODC without reading that file.
- **Architectural Scope:** Piper is kept strictly as a **development and offline fallback engine** (`TTS_PROVIDER=piper` / local fallback). It must never be bundled into a statically-linked, distributed proprietary binary.
- **Distribution Roadmap:** Prior to any public client release or standalone distribution:
  1. Isolate Piper behind an out-of-process **subprocess / IPC service boundary**, OR
  2. Adopt **Kokoro ONNX** (`kokoro-onnx` v0.6.1, ~82M parameters, Apache-2.0 permissive license) as the primary distributed local TTS engine.

### 5. Filler Evaluation

- Tested Orpheus on fillers (*"Hmm, I see."*, *"Uh, let me think."*, *"Wait, that changes it."*).
- Both Orpheus audio and Whisper transcription processed fillers accurately.
- To prevent synthetic artifacts or awkward latency pauses, **default `style.fillers = 0` (none)** until explicitly customized.

---

## Consequences

- Prevents quota exhaustion: automated testing and local development will never deplete the 100 req/hour Orpheus limit.
- Zero risk of silent failures: if Groq hits 429, a local/pre-recorded recovery line informs the user and switches output to the on-screen display.
- Clear distinction maintained between the Phase 0 smoke test and the rigorous Phase 1 benchmark corpus.
