# Project Status: Daimon (codename: Ekam / Baby)

**Profile:** A (Free)  
**Current Phase:** Phase 1 (Web Client, Telemetry & Barge-in)  
**Last Updated:** 2026-11-10  

> **Naming:** The assistant product name is **Daimon**, pronounced **DAY-mon** (/ˈdeɪmɒn/). The repository and internal package names remain `@ekam/*` until full trademark clearance and an explicit rename request from the project owner. The wake word is "Awaken" (Phase 1b).

---

## 1. Exit Criteria Checklist

### Phase 0 — Foundations
- [x] Monorepo scaffolded (`pnpm` workspaces for TS, `uv` for Python)
- [x] Git security guardrails verified (`.gitignore` protects `.env`, binary models, traces, and audio)
- [x] Profile A accounts verified (LiveKit Cloud, Groq, Google Gemini; Cloudflare account noted for future CDN/edge worker use, not currently in the Profile A voice hot path)
- [x] ADR-001 (initial stack) written (`docs/adr/001-initial-stack.md`)
- [x] ADR-002 (latency definitions) written (`docs/adr/002-latency-definitions.md`)
- [x] ADR-003 (Groq deviation & fallbacks) written (`docs/adr/003-groq-profile-a-stack-and-fallbacks.md`): notes Llama 3.3 70B 404 on free tier; pins `qwen/qwen3.8-27b`
- [x] Console agent smoke test talking back (`services/agent/agent.py`)
- [x] Initial smoke test run archived (`docs/benchmarks/phase_0_empirical_results.md`)
- [ ] **Bake-off corpus recorded** (speaker s01, sections A, C, E, G, I: 127 items / 254 clips) — **BLOCKING: Phase 1 Step 5 (Provider Bake-off) & Phase 1 Exit**

### Phase 1 — Web Client & Telemetry
- [x] Pinned latest stable Next.js (16.4.5) & React (19.3.1) patched against CVE-2025-55182; exact dependency pins (zero `^` ranges), frozen lockfile verified (`pnpm install --frozen-lockfile`)
- [x] Full `pnpm audit` and `pnpm audit --prod` clean (0 vulnerabilities) with temporary pnpm override resolving GHSA-g3hv-75wg-m249 (`minimatch@11.0.5`, requires Node $\ge 20$). *Note: Remove override once `eslint-config-next` ships a fixed dependency.*
- [x] Direct ESLint 9 runner configured (`apps/web/eslint.config.mjs`, `pnpm lint` 0 errors/warnings)
- [x] Next.js token route (`apps/web/src/app/api/token/route.ts`) loading root `.env` via `@next/env`, server-only secrets, 10m TTL, random identity, minimal grants
- [x] Web UI (`apps/web/src/app/page.tsx`) with animated reactive visualizer orb (`LISTENING`, `THINKING`, `SPEAKING`), live transcript feed, and `<RoomAudioRenderer>`
- [x] Appendix A v2 prompt integrated with dynamic `APP_NAME` ("Daimon"), style settings (`humor 1`, `fillers 0`, `formality 1`, `verbosity 1`), omitting voice tuning until Phase 3
- [x] TTS rolling hourly ceiling (100 req/hr) enforced via `GuardedOrpheusTTS`
- [x] **Spoken 429 recovery line regenerated locally with Piper** (`assets/recovery_429.wav`, 24 kHz mono 16-bit, zero API calls), wording: *"I've hit my voice limit, switching to my backup voice."* Matching on-screen fallback text emitted via `telemetry` data channel.
- [x] **Advanced 429 & Rate-Limit Handling in `GuardedOrpheusTTS`:**
  - Honors `Retry-After` header or falls back to capped exponential backoff (60s to 3600s).
  - Proactive switch to Piper fallback when remaining headroom $\le 10\%$ of limit.
  - Rolling request timestamps persisted to `tts_quota_timestamps.jsonl` (gitignored), surviving process restarts.
  - Automatic return to Orpheus when cooldown and rolling quota allow.
- [x] Local `LocalMockTTS` dev & test isolation guaranteeing automated test suites consume zero Groq Orpheus quota.
- [x] Client-measured `first_audio` telemetry published over LiveKit data channel (`telemetry` topic) and logged to `telemetry_traces.jsonl`.
- [x] Multi-tier LLM failover wired via `FallbackAdapter`: Groq (`qwen/qwen3.8-27b`) -> Gemini (`gemini-3.8-flash`) -> local Ollama (`qwen2.5:7b`), 5.0s attempt timeout.
- [x] **Opt-in Live LLM Tests (`services/agent/tests/test_live_llm.py`):** Added for Gemini 3.8 Flash and Ollama TTFT vs 5.0s timeout. Skipped by default in CI; requires explicit `$env:RUN_LIVE_LLM_TESTS=1`. Status: **not run** in automated verification (opt-in).
- [x] **Corpus Tooling & Sealed Split (Group B):**
  - Manifest created: `evals/corpus/manifest.json` (127 items / 254 clips for s01 sections A, C, E, G, I).
  - Validation tool: `evals/corpus/tools/check_corpus.py` (`status`, `validate`, `derive` without ffmpeg, pure wave/audioop).
  - Split assigner: `evals/corpus/tools/assign_split.py` (deterministic seeded split by item, stratified by section and env: 152 dev clips / 102 test clips).
  - Ground truth generated: `evals/corpus/ground_truth.json`.
  - Split lock committed: `evals/corpus/split.lock` (`result_runs: 0`).
- [x] **Provider Bake-Off Harness (Group C):**
  - Scaffolded at `evals/bakeoff/` with candidate registry (`config.yaml`), metrics (`wer.py`, `latency.py`, `compliance.py`), resumable file cache (`cache.py`), runner (`run_bakeoff.py`), and report generator (`report.py`).
  - Unit and smoke tests passing (12 tests offline, zero API calls).
  - Baseline report generated: `docs/benchmarks/phase_1_bakeoff.md` (labeled "SYNTHETIC, not a benchmark").
- [ ] **Live Browser Session & End-to-End Barge-In Measured:** Manual verification by owner following `docs/live_test_protocol.md` (user voice to silent speakers, target $\le 300\text{ ms}$).
- [ ] **Phase 1 Step 5 (Provider Bake-off Execution):** BLOCKED on recording the 127 bake-off clips.

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

1. **Bake-off Corpus Recording (Blocking Step 5 & Phase 1 Exit):** Owner must record s01 sections A, C, E, G, I (127 items, 254 clips) per `evals/corpus/RECORDING_GUIDE.md`. Run `check_corpus.py validate` after each session, then run `check_corpus.py derive`.
2. **Live Browser Verification & Barge-in (Owner Action):** Run the agent and web client locally, wear headphones, and follow `docs/live_test_protocol.md` to measure 10 barge-in trials in Audacity. Record median and p95 in this document.
3. **Opt-in Live LLM Tests Not Run in CI:** `services/agent/tests/test_live_llm.py` provides opt-in verification of Gemini 3.8 Flash TTFT and Ollama first-token time vs the 5.0s `attempt_timeout`. Status: **not run** in automated verification to prevent CI flakiness and unintended API costs. Run manually when desired: `$env:RUN_LIVE_LLM_TESTS=1; uv run --directory services/agent pytest tests/test_live_llm.py -v -s`.
4. **Piper TTS GPL-3.0 Scope:** Piper runtime is licensed under GPL-3.0 due to embedded `espeak-ng`. Kept strictly as a development and offline fallback engine (`TTS_PROVIDER=piper`). Prior to any public client distribution, isolate behind an out-of-process subprocess boundary or switch to Kokoro (Apache-2.0).
5. **RECORD_CORPUS=1 Mode Deferred:** In-browser WAV download via `MediaRecorder` is deferred. For web takes, record via OS-level communications audio or Audacity WASAPI loopback (noting that Audacity loopback captures raw mic without browser AEC).
6. **Naming & Trademark Clearance:** "Daimon" (pronounced DAY-mon) is a working product name with a known collision risk against existing software. Package names stay `@ekam/*` until full trademark opinion is obtained.
7. **Cloudflare Reference in Phase 0:** Cloudflare account was verified in Phase 0 onboarding, but no Cloudflare code is in the active Profile A voice pipeline. Reserved for Profile B asset hosting / Edge functions.

---

## 4. Next Tasks (In Priority Order)

1. **Owner:** Conduct manual live browser testing and measure 10 barge-in trials using headphones and Audacity per [`docs/live_test_protocol.md`](live_test_protocol.md). Log results in Section 1.
2. **Owner:** Record the 127 bake-off corpus items (254 clips) following [`evals/corpus/RECORDING_GUIDE.md`](../evals/corpus/RECORDING_GUIDE.md). Run `check_corpus.py status` and `validate` after each block, then run `check_corpus.py derive`.
3. **Execute Provider Bake-off:** Once real derived WAVs are in `evals/corpus/wavs/`, run `uv run --directory services/agent python evals/bakeoff/run_bakeoff.py --split dev --no-dry-run` to benchmark STT, LLM, and TTS candidates.
