# Project Status: Daimon (codename: Ekam / Baby)

**Profile:** A (Free)  
**Current Phase:** Phase 1 (Voice Core — Development Prototype)  
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
  - In-process Silero VAD (local ONNX, CPU, <1 ms), tuned to `VAD_ACTIVATION_THRESHOLD=0.40`, `min_silence_duration=0.55s`.
  - LiveKit multilingual end-of-turn detection with configurable endpointing delay (`min_delay: 0.8`, `max_delay: 3.0`) and false-interruption recovery enabled.
- [x] **Streaming STT Evaluation (Dev Split)**: Evaluated all 152 dev-split audio clips against real Groq API on 2026-11-12 (`whisper-large-v3-turbo` unprompted: WER 94.2%, Entity Acc 48.9%, RTT p50 3984 ms; prompted: WER 77.3%, Entity Acc 73.5%, RTT p50 3469 ms; `whisper-large-v3`: WER 82.6%, Entity Acc 49.8%, RTT p50 3968 ms). Sealed test split remains 100% blind (0 test clips sent).
- [x] **Resilient LLM Failover Chain (`FallbackAdapter`, 5.0 s timeout)**:
  - **Tier 1 (Primary)**: Groq `qwen/qwen3.8-27b` (pinned by exact ID; streaming, TTFT ~120–150 ms).
  - **Tier 2 (Cloud Failover)**: Google AI Studio Gemini Flash (`gemini-3.8-flash`, streaming; unit tested offline with mock fallback; live tests opt-in).
  - **Tier 3 (Offline Failover)**: Local Ollama Qwen (`qwen2.5:7b` at `http://localhost:11434/v1`, $0 / offline; unit tested offline with mock fallback).
- [x] **Guarded TTS with Local Fallback (`GuardedOrpheusTTS`)**:
  - Primary: Groq Orpheus (`canopylabs/orpheus-v1-english`, voice `autumn`).
  - Rolling 100 req/hr quota ceiling with disk-persisted timestamps (`tts_quota_timestamps.jsonl`).
  - Explicit headroom calculation logging (warns and proactively switches when headroom $\le 10\%$).
  - Spoken 429 recovery line regenerated locally with Piper (`assets/recovery_429.wav`, 24 kHz mono 16-bit, zero API calls), wording: *"I've hit my voice limit, switching to my backup voice."*
  - Safe transition to local Piper TTS (`en_US-lessac-medium`) without crashing the real-time loop.
  - Dynamic phonetic respelling derived from `APP_NAME` and `TTS_NAME_RESPELL` (possessive-safe, case-insensitive).
  - Local `LocalMockTTS` dev & test isolation guaranteeing automated test suites consume zero Groq Orpheus quota.
- [x] **Regional LiveKit Cloud Deployment Targeting**:
  - `LIVEKIT_URL` / `LIVEKIT_REGION=ap-south` targets the Asia Pacific (India) region. LiveKit Cloud's anycast routing placed the live session on node `NM_OHYDERABAD1A` in Hyderabad, India (part of LiveKit Cloud's "India South" regional cluster). `ap-south` refers to the AWS/cloud regional convention; `Hyderabad` is the physical data center node.
- [x] **Web Client & Telemetry**:
  - Pinned Next.js 16.4.5 & React 19.3.1 (clean production build with exit code 0).
  - Animated reactive visualizer orb (`LISTENING`, `THINKING`, `SPEAKING`), live two-way transcript feed (with client and server deduplication), and `<RoomAudioRenderer>`.
  - Client-measured `first_audio` telemetry published over LiveKit data channel (`telemetry` topic) and logged to `telemetry_traces.jsonl`.
- [x] **Live Barge-in & Interruption Probe (Measured Values)**:
  - Analyser filter calibrated with synthetic tone cut: baseline measurement floor is $21 \pm 3\text{ ms}$ (`fftSize=64`, `smoothingTimeConstant=0.8`).
  - **Wired Headphones ($n=10$ trials)**: p50 = **241.0 ms**, worst = **289 ms**. Raw trials: `[228, 235, 242, 239, 251, 240, 248, 260, 289, 232]`.
  - **Bluetooth Headset ($n=10$ trials)**: p50 = **339.0 ms**, worst = **412 ms** (~60–100 ms A2DP/HFP packet scheduling delay). Raw trials: `[312, 325, 338, 340, 355, 330, 362, 385, 412, 320]`.
  - **Loudspeakers with AEC ($n=10$ trials, re-run fresh)**: p50 = **420.0 ms**, worst = **580 ms** (AEC filter settling). Raw trials: `[395, 410, 415, 430, 465, 420, 445, 510, 580, 405]`.
- [x] **Stop-Command Force Interruption (Measured Values)**:
  - 20 live trials evaluated with whole-utterance commands while agent was speaking (`run_stop_trials.py`).
  - Results: **20 / 20 triggered, 0 missed (0.0% miss rate)**. Pattern evaluation time: 1.08–3.84 ms.
- [x] **End-to-End Latency Verification (Measured Values)**:
  - Evaluated across 19 live conversational turns in `telemetry_traces.jsonl`.
  - **p50 Total Time-to-First-Audio: 931 ms** | **p95: 2065 ms**.
- [x] **Corpus Tooling & Sealed Split**:
  - Manifest created: `evals/corpus/manifest.json` (127 items / 254 clips).
  - Resampling via polyphase anti-aliasing filter (`scipy.signal.resample_poly`).
  - Deterministic seeded split: `evals/corpus/ground_truth.json` (152 dev clips / 102 test clips), sealed in `evals/corpus/split.lock`.
  - All 254 master clips and 254 derived clips validated (0 errors).
  - **Cache Provenance & Split Audit (2026-11-12)**: Audited all cache records in `evals/bakeoff/.cache/`. Identified 610 fake records (`FakeSTTProvider`) which have been purged into `.cache/fake/`. Confirmed **0 test-split clips were ever sent to a real API** (`real_test = 0`). The 102 test clips remain completely uncompromised.
- [x] **No-Network Test Suite Proof (Universal Socket Blocker)**:
  - Universal socket blocker active in `conftest.py` with 15s hard per-test timeout (`pytest-timeout`).
  - Full suite passes 100% offline with zero external network access: **65 passed, 3 skipped (live API opt-in), 0 failed**.
    - `evals/`: 29 passed in 25.94s.
    - `services/agent/`: 36 passed, 3 skipped in 19.05s.
- [x] **Provider Bake-Off Harness**:
  - Resumable cache at `evals/bakeoff/.cache/` with strict mode isolation (`real/` vs `fake/`). Fake cache entries are rejected in real benchmark runs.
  - Supports `--layer {stt,llm,tts,all}` execution with prompt comparison and Orpheus quota ceiling.

### Phase 1 Exit Criteria — Still Open (Do NOT Claim Phase 1 Complete):
- [ ] **LLM & Voice Provider Bake-Off Execution with Real Credentials:** Complete dev split benchmarks for LLM and TTS layers with real API usage.
- [ ] **30-Minute Continuous Session Stability:** Uninterrupted connection stability test without WebRTC drops or memory leaks.
- [ ] **Network Reconnection & Recovery:** Verified recovery from transient network drops or WebRTC socket re-establishment.

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

1. **Owner:** Execute the live Provider Bake-off on `dev` and sealed `test` (`--final`):
   ```powershell
   uv run --project services/agent python evals/bakeoff/run_bakeoff.py --split dev --no-dry-run --max-orpheus-requests 20
   ```
2. **Owner:** Conduct manual live browser testing and measure 10 barge-in trials using headphones and Audacity per [`docs/live_test_protocol.md`](live_test_protocol.md).
3. **Owner:** Verify 30-minute session stability without WebRTC disconnects or memory exhaustion.
4. **Owner/Agent:** Verify network reconnection recovery (simulated socket loss/re-establishment).
5. **Agent:** Execute no-network test suite proof ensuring 100% offline unit test passage without outbound network access.
