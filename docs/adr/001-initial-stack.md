# ADR-001: Initial Architecture & Technology Stack (Profile A)

**Status:** Accepted  
**Date:** 2026-11-07  
**Author:** Ekam Core Team  
**Scope:** Phase 0–1 Foundations & Core Loop  

---

## Context

Baby is an ultra-low-latency, voice-first personal AI assistant. To maintain rapid development velocity while avoiding unnecessary early cloud costs, the project adopts a strict two-profile build strategy:
1. **Profile A (Free):** Use free tiers, local on-device models, and open-source components.
2. **Profile B (Premium):** Upgrade specific layers to dedicated paid infrastructure only when empirical telemetry benchmarks identify a specific layer as the bottleneck.

Every external layer sits behind a modular interface to allow zero-rewrite provider swapping.

---

## Decision

The initial stack for **Profile A** is defined as follows:

| Layer | Selection | Justification |
|---|---|---|
| **Transport** | LiveKit Cloud (Free Build plan, `ap-south` Mumbai) | Handles real-time WebRTC, echo cancellation, adaptive audio jitter, and connection resilience. |
| **Agent Framework** | `livekit-agents` (Python 3.12, pinned v1.8.11) | First-party async framework with native turn handling, Silero integration, and streaming session lifecycle. |
| **VAD** | Silero VAD (ONNX, CPU) | In-process, zero network round-trip, robust speech/silence boundary detection loaded once per worker. |
| **End of Turn** | Hybrid (Silero min silence + adaptive endpointing) | Prevents premature turn cutoffs without incurring additional model hops on the hot path. |
| **STT** | Groq Whisper (`whisper-large-v3-turbo`) | Fast streaming transcription with generous free tier; evaluated alongside Deepgram in Phase 1 bake-off. |
| **Fast LLM** | Groq `llama-3.3-70b-versatile` | Extremely low TTFT (~120–250 ms) on Groq LPUs; thinking/reasoning disabled on the voice fast path. |
| **Reasoning Fallback** | Google Gemini 2.5 Flash / Pro (Free Tier) | Accessible for deeper, non-hot-path tasks or secondary failover. |
| **TTS** | Groq Orpheus (`canopylabs/orpheus-v1-english`, voice `autumn`) | Natural speech synthesis hosted via Groq's low-latency API without upfront cost. |
| **Tool Gateway** | Node.js + Fastify + TypeScript (planned Phase 3) | Typed API server managing OAuth, tool permissions, and persistent state outside the voice hot path. |
| **Database & Cache** | PostgreSQL (+ pgvector) + Redis (planned Phase 3) | Single relational and vector store for long-term memory; Redis for session state and BullMQ background queues. |
| **Package Management** | `pnpm` (Node monorepo) + `uv` (Python) | High-speed, lockfile-reproducible package and virtual environment management. |

---

## Consequences

- **Zero Cost Baseline:** Enables complete functional validation of the voice loop and deterministic tools without ongoing cloud spend.
- **Provider Swapping Readiness:** All model and transport bindings are abstracted behind provider configuration, ensuring clean migration to Profile B (Cartesia/Deepgram Flux/Ship tier) when triggered by benchmark metrics.

