# Project Status: Daimon (codename: Ekam / Baby)

**Profile:** A (Free)  
**Current Phase:** Phase 1 (Web Client, Telemetry & Barge-in)  
**Last Updated:** 2026-11-09  

> **Naming:** The project and assistant are now named **Daimon**, pronounced **DAY-mon** (/ˈdeɪmɒn/). The repo, paths, package names and `APP_NAME` ("Ekam") have **not** been renamed yet. See Next Tasks. Until then, "Ekam" in code and older docs refers to this project.

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
- [ ] **Bake-off corpus recorded** (speaker s01, sections A, C, E, G, I of `evals/corpus/RECORDING_GUIDE.md` v2: 127 items, about 254 clips at 2 takes, plus ground truth mapping and dev/test split assigned) — **BLOCKING: Phase 1 Step 5 (Bake-off) & Phase 1 Exit**

### Phase 1 — Web Client & Telemetry
- [x] Pinned latest stable Next.js (16.4.5) & React (19.3.1) patched against CVE-2025-55182; exact dependency pins (zero `^` ranges), frozen lockfile verified (`pnpm install --frozen-lockfile`)
- [x] Full `pnpm audit` and `pnpm audit --prod` clean (0 vulnerabilities) with temporary pnpm override resolving GHSA-g3hv-75wg-m249 (`minimatch@11.0.5`, requires Node $\ge 20$). *Note: Remove override once `eslint-config-next` ships a fixed dependency.*
- [x] Direct ESLint 9 runner configured (`apps/web/eslint.config.mjs`, `pnpm lint` 0 errors/warnings)
- [x] Next.js token route (`apps/web/src/app/api/token/route.ts`) loading root `.env` via `@next/env`, server-only secrets, 10m TTL, random identity, minimal grants
- [x] Web UI (`apps/web/src/app/page.tsx`) with animated reactive visualizer orb (`LISTENING`, `THINKING`, `SPEAKING`), live transcript feed, and `<RoomAudioRenderer>`
- [x] Appendix A v2 prompt integrated with `APP_NAME` ("Ekam"), style settings (`humor 1`, `fillers 0`, `formality 1`, `verbosity 1`), omitting voice tuning until Phase 3
- [x] TTS rolling hourly ceiling (100 req/hr) enforced via `GuardedOrpheusTTS`
- [x] Spoken 429 recovery line pre-recorded (`assets/recovery_429.wav`, 24 kHz mono) with zero API calls + on-screen text fallback
- [x] Local `LocalMockTTS` dev & test isolation guaranteeing automated test suites consume zero Groq Orpheus quota
- [x] Client-measured `first_audio` telemetry published over LiveKit data channel (`ekam-telemetry`) and logged to JSONL traces
- [x] Automated barge-in test suite (`services/agent/tests/test_barge_in.py`):
  - Task-cancel latency (mock): 0.06 ms. This measures the code path of cancelling the speech task in a test harness, **not** user-perceived barge-in. It passes the $\le 300\text{ ms}$ requirement only for that narrow definition.
  - False-interruption recovery: transient 150 ms cough ignored, speech resumed
  - Quota enforcement verified: engages pre-recorded recovery on limit
- [ ] **End-to-end barge-in measured in a live session** (user voice to silent speakers, including audio buffers, echo-cancellation settling and TTS flush), against a target set before testing
- [ ] Phase 1 Step 5 (Provider Bake-off) — **BLOCKED on the bake-off corpus**

### Phase 1b — Wake Word, Session Gate & Name Addressing (Proposed)
Design is defined in the Proposed ADR-004 below. Nothing in this phase is built or benchmarked.

- [ ] ADR-004 (wake-word and session architecture) written as **Proposed** (`docs/adr/004-wake-word-and-session-architecture.md`)
- [ ] **Wake-word corpus recorded** (`RECORDING_GUIDE.md` v2): s01 sections B, D, F, H (51 items); speakers s02–s05 subset (45 items each); continuous negative audio (hours of TV, chatter, calls, music, podcasts)
- [ ] On-device pre-gating layer chosen (browser WASM/worker for the web client; native later) and benchmarked on target hardware
- [ ] "Awaken" session gate: detector meets false-accept and true-positive targets set before testing
- [ ] Name gate ("Daimon" at the start or end of an utterance while AWAKE) with an alias map built from corpus section E raw STT logs
- [ ] Session states (`ASLEEP` / `AWAKE`), sleep and abort phrases, idle timeout
- [ ] Visual feedback on wake (Orb glow), chime on confirmed wake, descending chime on sleep
- [ ] ADR-004 moved to **Accepted** only when benchmarks meet its acceptance criteria

---

## 2. Decisions (ADRs)
- [ADR-001: Initial Architecture & Technology Stack (Profile A)](docs/adr/001-initial-stack.md)
- [ADR-002: Latency Contracts, Timeline Definitions, and Measurement Protocol](docs/adr/002-latency-definitions.md)
- [ADR-003: Groq Pipeline as Profile A Deviation, Model Pinning, Rate Limits, and Fallback Architecture](docs/adr/003-groq-profile-a-stack-and-fallbacks.md)
- **ADR-004: Wake-Word and Session Architecture — PROPOSED, not yet written.** Summary of the intended v1.1 design:
  - **Wake word:** "Awaken" only, said as a standalone utterance (short pause before and after). Opens the session (`ASLEEP` to `AWAKE`).
  - **Addressing:** while `AWAKE`, the name "Daimon" (aliases Damon, Dayman, Demon, normalized to "Daimon") must appear at the **start or end** of an utterance for it to reach the cloud. Speech without the name is dropped on-device with no cloud call.
  - **Abort (stays AWAKE):** "stop" (during TTS), "cancel that", "never mind", "Daimon, stop".
  - **Sleep (to `ASLEEP`):** "dismissed", "that's all", "go to sleep", "Daimon, sleep", and combined or tail forms. Idle timeout also sleeps the session (length to be tuned).
  - **Feedback:** Orb glow and chime on confirmed wake. The assistant's TTS always says DAY-mon.
  - **Deferred until real data exists:** speaker verification, a two-stage verifier, the LLM addressee check (`<skip/>` or `ignore_turn` tool call), a follow-up leash without the name.
  - **Open items to decide before Accepted:** "Awaken" followed directly by a command in one breath, a "Hey Daimon" carrier prefix, bare "Daimon" behavior, idle-timeout length, on-device engine choice.

---

## 3. Open Questions / Blockers
1. **Blocking for Phase 1 Exit & Step 5 Bake-off:** the bake-off corpus (s01 sections A, C, E, G, I of `evals/corpus/RECORDING_GUIDE.md` v2, 127 items) must be recorded and its ground truth validated. The previous 53-item scope (including 20 "Ekam" wake-word repetitions) is superseded.
2. **Untested Live Verification:** The `apps/web/src/components/VoiceRoom.tsx` transcript state refactor (deriving merged transcripts from data channel and LiveKit hook via `useMemo` instead of `useEffect` `setState`) compiles cleanly, passes ESLint and Next.js production build, but remains **untested in a live WebRTC audio session** with an active running agent. The live session is also where end-to-end barge-in should be measured.
3. **Temporary Minimatch Override:** The root `package.json` contains `pnpm.overrides` for `minimatch@>=7.0.0 <11.0.1: 11.0.5` strictly to patch dev-only advisory GHSA-g3hv-75wg-m249 from `eslint-config-next`. `minimatch@11` requires Node $\ge 20$ (local machine: `v22.13.1`). **Remove this override** once `eslint-config-next` releases an update with a fixed upstream dependency to avoid leaving invisible baggage.
4. **On-device pre-gating is not in the stack.** ADR-003 covers Groq and fallbacks, but dropping non-wake audio before the cloud needs a local layer. On the web client, a tab must keep the mic open and run a keyword model in WASM or a worker. Decide this in ADR-004 before recording the wake-word portions.
5. **Name collision and spelling.** "Daimon" pronounced DAY-mon sounds like the first name "Damon" and like "Dayman" and "demon", and STT will often write it as Damon, Daemon or Demon. Search for existing products, trademarks and domains called Daimon before committing publicly. The alias map should come from corpus section E, not from guesses.
6. **Policy items still open** (corpus records them as informational until decided): "Awaken" plus command in one breath, "Hey Daimon" prefix, "Awaken" with a short pause or right after other speech, bare "Daimon" behavior.
7. **Statistical limit on false-accept claims.** With zero false accepts observed, the "rule of three" gives a rate upper bound of roughly 3 divided by hours recorded. Showing under 0.1 per hour needs about 30 hours with none. Report the actual bound reached rather than the target.

---

## 4. Next Tasks
1. Record the **bake-off corpus** (s01 sections A, C, E, G, I) following `evals/corpus/RECORDING_GUIDE.md` v2. Replace the old guide in the repo, and assign the dev/test split before running any detector or provider.
2. Run the automated provider bake-off (STT, LLM, TTS) once the corpus WAVs are present. Use section E raw STT output to build the alias map.
3. Live test the web client with a running agent (transcript feed, visualizer orb animation) and measure **end-to-end barge-in** there.
4. Deploy to LiveKit Cloud `ap-south` (Mumbai) and measure production latency.
5. Write **ADR-004** as Proposed, with acceptance criteria and thresholds set before any test run.
6. Record the **wake-word corpus** (s01 sections B, D, F, H; speakers s02–s05; continuous negative audio). If other speakers can't be recruited, label all wake-word results "single-speaker baseline".
7. Decide the project rename: update the repo name, `APP_NAME`, prompt text, UI strings and `ekam-telemetry` channel name to Daimon, or keep "Ekam" as an internal codename and document that choice here.
8. **Periodic Security Cadence:** Re-run full `pnpm audit` at the start of Phase 3 and every few weeks thereafter.