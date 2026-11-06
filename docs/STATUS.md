# Project Status: Ekam (Baby)

**Profile:** A (Free)  
**Current Phase:** Phase 0 (Foundations) → Phase 1 Transition  
**Last Updated:** 2026-11-07  

---

## 1. Exit Criteria Checklist

### Phase 0 — Foundations
- [x] Monorepo scaffolded (`pnpm` workspaces for TS, `uv` for Python)
- [x] Git security guardrails verified (`.gitignore` protects `.env`)
- [x] Profile A accounts verified (LiveKit Cloud, Groq, Google Gemini, Cloudflare)
- [x] ADR-001 (initial stack) written (`docs/adr/001-initial-stack.md`)
- [x] ADR-002 (latency definitions) written (`docs/adr/002-latency-definitions.md`)
- [x] Console agent smoke test talking back (`services/agent/agent.py`)
- [x] Empirical baseline stats archived (`docs/benchmarks/phase_0_empirical_results.md`)
- [ ] Benchmark corpus recorded (50–100 WAVs + wake word repetitions in `evals/corpus/`) — *Pending user recording*

---

## 2. Decisions (ADRs)
- [ADR-001: Initial Architecture & Technology Stack (Profile A)](file:///c:/Aagosh/CODE/Ekam/docs/adr/001-initial-stack.md)
- [ADR-002: Latency Contracts, Timeline Definitions, and Measurement Protocol](file:///c:/Aagosh/CODE/Ekam/docs/adr/002-latency-definitions.md)

---

## 3. Open Questions
1. When user records the benchmark corpus: include the ~20 repetitions of the wake word ("Ekam") and ~10–20 code-mixed Hindi utterances as specified in updated `BABY_ROADMAP.md`?

---

## 4. Next 3 Tasks
1. **P0-Exit / Phase 1 Kickoff:** Finalize benchmark corpus recordings (`evals/corpus/`).
2. **Phase 1 Step 2 (Web Client Scaffolding):** Build minimal Next.js frontend in `apps/web/` with LiveKit token minting route.
3. **Phase 1 Step 3 & 4 (Web UI + Telemetry):** Connect web client to LiveKit room with voice orb, audio renderer, and per-turn telemetry stream.

---

## 5. Known Issues
- `llama-3.3-70b-versatile` unavailable on default Groq tier; resolved by mapping fast LLM to Groq `qwen/qwen3.8-27b` (empirically measured at 129–181 ms TTFT).
- Groq TTS requires one-time terms acceptance in Groq console for `canopylabs/orpheus-v1-english` (completed).
