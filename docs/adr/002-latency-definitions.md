# ADR-002: Latency Contracts, Timeline Definitions, and Measurement Protocol

**Status:** Accepted  
**Date:** 2026-11-07  
**Author:** Ekam Core Team  
**Scope:** Telemetry & Performance Standards across all Phases  

---

## Context

Conversational voice assistants feel natural only when the response latency approaches typical human conversational gaps (~200–300 ms). Latency numbers reported by AI vendors (e.g., TTFT or TTFB in isolation) often hide transport delays, VAD confirmation windows, network hops, and playback buffering.

To prevent optimization blindspots, Baby defines a formal, end-to-end latency contract where client-observed time is the definitive truth.

---

## Timeline & Metric Definitions

All measurements are referenced against ground truth speech in recorded evaluation sessions:

```text
User speaks:  [── Speech ──]
Time:         T_start     T_end       T_eot     T_stt     T_llm_1   T_tts_1     T_first_audio
                             │          │         │         │         │             │
                             └──────────┴─────────┴─────────┴─────────┴─────────────┘
                                          End-to-End Latency Window (≤ 900 ms p50)
```

| Timestamp | Symbol | Definition |
|---|---|---|
| User Speech Start | $T_{\text{start}}$ | The millisecond user voice activity begins (measured via ground-truth audio). |
| User Speech End | $T_{\text{end}}$ | The exact physical moment the user ceases vocalization. |
| VAD Silence Threshold | $T_{\text{vad}}$ | Silence duration required by Silero (configured at 400–550 ms) before triggering turn boundary. |
| End-of-Turn Decided | $T_{\text{eot}}$ | The moment the turn-detector confirms the user has finished their conversational turn. |
| STT Finalized | $T_{\text{stt}}$ | The moment final recognized text is received from the STT provider. |
| Router Decision | $T_{\text{router}}$ | Execution duration of Tier-0 rule matching (target ≤ 20 ms). |
| LLM First Token | $T_{\text{llm\_1}}$ | Time-to-First-Token (TTFT) emitted by the primary model. |
| TTS First Byte | $T_{\text{tts\_1}}$ | Time-to-First-Byte (TTFB) of synthesized audio returned from the TTS engine. |
| First Audio Played | $T_{\text{first\_audio}}$ | First audio frame emitted by the client speaker/headphone device. |

### The Core Contract: Speech-End to First-Audio
$$\text{Latency} = T_{\text{first\_audio}} - T_{\text{end}}$$

- **Fast-path budget (p50):** $\le 900\text{ ms}$
- **Fast-path alarm (p95):** $\le 1500\text{ ms}$
- **Tier-0 (deterministic tools):** $\le 500\text{ ms}$
- **Barge-in (speech onset to silence):** $\le 250\text{ ms}$

---

## The Hot-Path Invariant

The **voice hot path** is strictly defined as all synchronous computation and I/O executed between $T_{\text{end}}$ and $T_{\text{first\_audio}}$.

1. **Permitted on the hot path:**
   - In-memory lookups & pre-warmed connections
   - Local deterministic rule matching (regex / simpleeval)
   - Streaming calls to STT, LLM, and TTS
   - Fast, read-only cache hits (≤ 5 ms)
2. **Forbidden on the hot path:**
   - Synchronous relational database queries (PostgreSQL)
   - Synchronous embedding API network calls
   - Blocking disk I/O or non-streamed HTTP logging
   - Opening new TCP/TLS connections

All telemetry, audit logging, long-term memory embedding, and analytics are asynchronous write-behind tasks offloaded to background workers.

---

## Telemetry Format

Every conversation turn emits a structured JSON record:

```json
{
  "trace_id": "018f3a9e-...",
  "turn": 1,
  "t": {
    "speech_end": 0,
    "eot_decided": 320,
    "stt_final": 350,
    "router": 362,
    "llm_first_token": 580,
    "tts_first_byte": 690,
    "first_audio": 780
  },
  "tier": 1,
  "interrupted": false,
  "cost_usd": 0.00018
}
```

