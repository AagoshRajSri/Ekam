# Project Status: Ekam (Baby)

**Profile:** A (Free)  
**Current Phase:** Phase 1 (Web Client, Telemetry & Barge-in)  
**Last Updated:** 2026-11-07  

---

## 1. Exit Criteria Checklist

### Phase 0 — Foundations
- [x] Monorepo scaffolded (`pnpm` workspaces for TS, `uv` for Python)
- [x] Git security guardrails verified (`.gitignore` protects `.env`)
- [x] Profile A accounts verified (LiveKit Cloud, Groq, Google Gemini, Cloudflare)
- [x] ADR-001 (initial stack) written (`docs/adr/001-initial-stack.md`)
- [x] ADR-002 (latency definitions) written (`docs/adr/002-latency-definitions.md`)
- [x] ADR-003 (Groq deviation & fallbacks) written (`docs/adr/003-groq-profile-a-stack-and-fallbacks.md`)
- [x] Console agent smoke test talking back (`services/agent/agent.py`)
- [x] Initial smoke test run archived (`docs/benchmarks/phase_0_empirical_results.md`)
- [ ] Benchmark corpus recorded (53 WAVs + wake word repetitions in `evals/corpus/`) — **BLOCKING: Phase 1 Step 5 (Bake-off) & Phase 1 Exit**

### Phase 1 — Web Client & Telemetry
- [x] Pinned latest stable Next.js (16.4.5) & React (19.3.1) patched against CVE-2025-55182; exact dependency pins (zero `^` ranges), frozen lockfile verified (`pnpm install --frozen-lockfile`), production audit clean (0 vulnerabilities), direct ESLint 9 runner configured (`pnpm lint` 0 errors/warnings)
- [x] Next.js token route (`apps/web/src/app/api/token/route.ts`) loading root `.env` via `@next/env`, server-only secrets, 10m TTL, random identity, minimal grants
- [x] Ekam Web UI (`apps/web/src/app/page.tsx`) with animated reactive visualizer orb (`LISTENING`, `THINKING`, `SPEAKING`), live transcript feed, and `<RoomAudioRenderer>`
- [x] Appendix A v2 prompt integrated with `APP_NAME` ("Ekam"), style settings (`humor 1`, `fillers 0`, `formality 1`, `verbosity 1`), omitting voice tuning until Phase 3
- [x] TTS rolling hourly ceiling (100 req/hr) enforced via `GuardedOrpheusTTS`
- [x] Spoken 429 recovery line pre-recorded (`assets/recovery_429.wav`, 24 kHz mono) with zero API calls + on-screen text fallback
- [x] Local `LocalMockTTS` dev & test isolation guaranteeing automated test suites consume zero Groq Orpheus quota
- [x] Client-measured `first_audio` telemetry published over LiveKit data channel (`ekam-telemetry`) and logged to JSONL traces
- [x] Automated barge-in test suite (`services/agent/tests/test_barge_in.py`):
  - Cut-off latency: 0.06 ms (passing $\le 300\text{ ms}$ requirement)
  - False-interruption recovery: transient 150 ms cough ignored, speech resumed
  - Quota enforcement verified: engages pre-recorded recovery on limit
- [ ] Phase 1 Step 5 (Provider Bake-off) — **BLOCKED on audio corpus recording**

---

## 2. Decisions (ADRs)
- [ADR-001: Initial Architecture & Technology Stack (Profile A)](docs/adr/001-initial-stack.md)
- [ADR-002: Latency Contracts, Timeline Definitions, and Measurement Protocol](docs/adr/002-latency-definitions.md)
- [ADR-003: Groq Pipeline as Profile A Deviation, Model Pinning, Rate Limits, and Fallback Architecture](docs/adr/003-groq-profile-a-stack-and-fallbacks.md)

---

## 3. Open Questions / Blockers
1. **Blocking for Phase 1 Exit & Step 5 Bake-off:** Benchmark audio corpus must be recorded per `evals/corpus/RECORDING_GUIDE.md` (53 items: 23 Tier 0/context/corrections + 10 Hindi/mixed + 20 "Ekam" wake word repetitions).

---

## 4. Next Tasks
1. Record audio corpus following `evals/corpus/RECORDING_GUIDE.md`.
2. Run automated provider bake-off (STT, LLM, TTS) once corpus WAVs are present.
3. Deploy to LiveKit Cloud `ap-south` (Mumbai) and measure production latency.
