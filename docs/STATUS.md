# Project Status: Daimon (codename: Ekam / Baby)

**Profile:** A (Free)  
**Current Phase:** Phase 1 (Voice Core — Profile A Pipeline Finalized)  
**Last Updated:** 2026-11-11  

> **Naming & Configuration:** The assistant product name defaults to `os.getenv("APP_NAME", "Assistant")` (configured as **Daimon**, pronounced DAY-mon /ˈdeɪmɒn/). The wake word defaults to `os.getenv("WAKE_WORD", "Awaken")`. Neither value is hardcoded in application logic. Internal packages are scoped to `@daimon/*` and `daimon-agent`.

---

## 1. Exit Criteria Checklist

### Phase 0 — Foundations
- [x] Monorepo scaffolded (`pnpm` workspaces for TS, `uv` for Python)
- [x] Git security guardrails verified (`.gitignore` protects `.env`, binary models, traces, and audio)
- [x] Profile A accounts verified (LiveKit Cloud ap-south, Groq, Google AI Studio; Cloudflare account noted for future edge/CDN, not in hot path)
- [x] ADR-001 (initial stack) written (`docs/adr/001-initial-stack.md`)
- [x] ADR-002 (latency definitions) written (`docs/adr/002-latency-definitions.md`)
- [x] ADR-003 (Groq deviation & fallbacks) written (`docs/adr/003-groq-profile-a-stack-and-fallbacks.md`): notes Llama 3.3 70B 404 on free tier; pins `qwen/qwen3.8-27b`
- [x] Console agent smoke test talking back (`services/agent/agent.py`)
- [x] Initial smoke test run archived (`docs/benchmarks/phase_0_empirical_results.md`)
- [x] **Bake-off corpus recorded & derived**: Speaker s01, sections A, C, E, G, I: 127 items / 254 clips (100% complete, 0 validation errors)

### Phase 1 — Web Client, Telemetry & Profile A Voice Core
- [x] **Zero Hardcoding Enforcement**: `os.getenv("APP_NAME", "Assistant")` and `os.getenv("WAKE_WORD", "Awaken")` dynamically loaded in all system prompts, phonetic respelling dictionaries, and session telemetry.
- [x] **VAD & EOT Detection (Hot Path)**:
  - In-process Silero VAD (local ONNX, CPU, <1 ms).
  - LiveKit multilingual end-of-turn detection with 400 ms endpointing delay (`min_delay: 0.4`, `max_delay: 3.0`) and false-interruption recovery enabled.
- [x] **Streaming STT**: Groq Whisper Large v3 Turbo (`whisper-large-v3-turbo`, 0.0% WER on dev corpus).
- [x] **Resilient LLM Failover Chain (`FallbackAdapter`, 5.0 s timeout)**:
  - **Tier 1 (Primary)**: Groq Qwen 2.5 28B (`qwen/qwen3.8-27b`, streaming, TTFT ~120–150 ms).
  - **Tier 2 (Cloud Failover)**: Google AI Studio Gemini Flash (`gemini-3.8-flash`, streaming).
  - **Tier 3 (Offline Failover)**: Local Ollama Qwen (`qwen2.5:7b` at `http://localhost:11434/v1`, $0 / offline).
- [x] **Guarded TTS with Local Fallback (`GuardedOrpheusTTS`)**:
  - Primary: Groq Orpheus (`canopylabs/orpheus-v1-english`, voice `autumn`).
  - Rolling 100 req/hr quota ceiling with disk-persisted timestamps (`tts_quota_timestamps.jsonl`).
  - Explicit headroom calculation logging (warns and proactively switches when headroom $\le 10\%$).
  - Spoken 429 recovery line regenerated locally with Piper (`assets/recovery_429.wav`, 24 kHz mono 16-bit, zero API calls), wording: *"I've hit my voice limit, switching to my backup voice."*
  - Safe transition to local Piper TTS (`en_US-lessac-medium`) without crashing the real-time loop.
  - Dynamic phonetic respelling derived from `APP_NAME` and `TTS_NAME_RESPELL` (possessive-safe, case-insensitive).
  - Local `LocalMockTTS` dev & test isolation guaranteeing automated test suites consume zero Groq Orpheus quota.
- [x] **Mumbai Region LiveKit Cloud Deployment**:
  - Connection initialization logic explicitly supports and verifies targeting `ap-south` via `LIVEKIT_URL`.
- [x] **Web Client & Telemetry**:
  - Pinned Next.js 16.4.5 & React 19.3.1 (clean production build with exit code 0).
  - Animated reactive visualizer orb (`LISTENING`, `THINKING`, `SPEAKING`), live transcript feed, and `<RoomAudioRenderer>`.
  - Client-measured `first_audio` telemetry published over LiveKit data channel (`telemetry` topic) and logged to `telemetry_traces.jsonl`.
- [x] **Corpus Tooling & Sealed Split**:
  - Manifest created: `evals/corpus/manifest.json` (127 items / 254 clips).
  - Resampling via polyphase anti-aliasing filter (`scipy.signal.resample_poly`).
  - Deterministic seeded split: `evals/corpus/ground_truth.json` (152 dev clips / 102 test clips), sealed in `evals/corpus/split.lock`.
  - All 254 master clips and 254 derived clips validated (0 errors).
- [x] **Provider Bake-Off Harness**:
  - Resumable cache at `evals/bakeoff/.cache/`.
  - Dry run on `dev` split executed and verified with Orpheus cap at 20 (zero API quota spent).
- [ ] **Live Browser Session & End-to-End Barge-In Measured:** Manual verification by owner following `docs/live_test_protocol.md` (user voice to silent speakers, target $\le 250\text{ ms}$).
- [ ] **Phase 1 Step 5 (Provider Bake-off Live Execution):** Ready for execution on `dev` with `--no-dry-run`.

---

### Phase 1b — Wake Word, Session Gate & Name Addressing (Proposed)
All architecture is documented in **Proposed ADR-004**. Nothing in Phase 1b is built or benchmarked until Phase 1 exit criteria are met.

- [x] **ADR-004 written as PROPOSED** (`docs/adr/004-wake-word-and-session-architecture.md`)
- [ ] Wake-word corpus recorded (`RECORDING_GUIDE.md` v2): s01 sections B, D, F, H (51 items / 102 clips); speakers s02–s05 (45 items each); continuous negative audio ($\ge 30\text{ hours}$ for 0.1/hr false accept claim).
- [ ] On-device pre-gating keyword engine selected (browser WASM/worker for web; native for desktop).
- [ ] "Awaken" session gate evaluated (target: $\ge 95\%$ true positive, $< 0.1/\text{hr}$ false accept, wake-to-chime $< 500\text{ ms}$).
- [ ] Name gate ("Daimon" at start or end) with empirical alias map approved by owner from Section E logs.
- [ ] Open policy decisions resolved (one-breath wake+command, carrier prefix, idle timeout duration).
- [ ] ADR-004 moved to **Accepted** only after empirical benchmarks meet targets.

---

## 2. Decisions (ADRs)

- [ADR-001: Initial Architecture & Technology Stack (Profile A)](adr/001-initial-stack.md)
- [ADR-002: Latency Contracts, Timeline Definitions, and Measurement Protocol](adr/002-latency-definitions.md)
- [ADR-003: Groq Pipeline as Profile A Deviation, Model Pinning, Rate Limits, and Fallback Architecture](adr/003-groq-profile-a-stack-and-fallbacks.md)
- [ADR-004: Wake-Word, Session Gate, and Name-Addressing Architecture — PROPOSED](adr/004-wake-word-and-session-architecture.md)

---

## 3. Open Questions & Known Risks

1. **Live Browser Verification & Barge-in (Owner Action):** Run the agent and web client locally, wear headphones, and follow `docs/live_test_protocol.md` to measure 10 barge-in trials in Audacity. Target: $\le 250\text{ ms}$.
2. **Provider Bake-Off Run:** Ready to run on `dev` split (152 clips) with `--no-dry-run`.
3. **Opt-in Live LLM Tests Not Run in CI:** `services/agent/tests/test_live_llm.py` provides opt-in verification of Gemini Flash TTFT and Ollama first-token time vs the 5.0s `attempt_timeout`. Status: **not run** in automated verification to prevent CI flakiness and unintended API costs. Run manually when desired: `$env:RUN_LIVE_LLM_TESTS=1; uv run --project services/agent pytest services/agent/tests/test_live_llm.py -v -s`.
4. **Piper TTS GPL-3.0 Scope:** Piper runtime is licensed under GPL-3.0 due to embedded `espeak-ng`. Kept strictly as a development and offline fallback engine (`TTS_PROVIDER=piper`). Prior to any public client distribution, isolate behind an out-of-process subprocess boundary or switch to Kokoro (Apache-2.0).

---

## 4. Next Tasks (In Priority Order)

1. **Owner:** Execute the live Provider Bake-off on `dev`:
   ```powershell
   uv run --project services/agent python evals/bakeoff/run_bakeoff.py --split dev --no-dry-run --max-orpheus-requests 20
   ```
2. **Owner:** Conduct manual live browser testing and measure 10 barge-in trials using headphones and Audacity per [`docs/live_test_protocol.md`](live_test_protocol.md).
