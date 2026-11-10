# ADR-004: Wake-Word, Session Gate, and Name-Addressing Architecture

**Status:** Proposed  
**Date:** 2026-11-10  
**Author:** Ekam Core Team  
**Scope:** Phase 1b — On-device Pre-gating, Session State Machine, and Per-Utterance Name Gate  

---

## Context

Per Specification §3.7, cloud voice pipelines incur high latency, token cost, and privacy concerns if all ambient audio is streamed to external LLM/STT APIs. To prevent streaming unaddressed conversation or background noise, the system requires a multi-tier gating architecture executed strictly on-device before any network transmission:

1. **Session Gate (`ASLEEP` -> `AWAKE`):** The device listens locally for the wake word **"Awaken"**.
2. **Per-Utterance Name Gate (while `AWAKE`):** Utterances must be addressed to the assistant by name (**"Daimon"**, pronounced DAY-mon, or recognized phonetic aliases) at the beginning or end of speech. Speech without the name is dropped on-device.
3. **Session Closure (`AWAKE` -> `ASLEEP`):** Explicit sleep phrases or an idle timeout transition the system back to sleep.
4. **Abort (stays `AWAKE`):** Cutoff phrases cancel the in-flight response without closing the session.

This ADR formalizes the proposed state machine, specifies acceptance thresholds set before recording, documents open policy decisions, and establishes the on-device evaluation protocol.

> [!IMPORTANT]
> **This ADR is Proposed. Nothing in Phase 1b is built or benchmarked.**
> This document governs the future implementation once the Phase 1 Provider Bake-off is complete and the corpus has been recorded.

---

## Decision (Proposed Design v1.1)

### 1. Session State Machine

```
               ┌────────────────────────────────────────────────────────┐
               │                                                        │
               ▼                                                        │
         ┌───────────┐         "Awaken" (standalone)          ┌─────────┴─┐
         │           ├───────────────────────────────────────►│           │
         │  ASLEEP   │   [Ascending Chime + Visual Orb Glow]   │   AWAKE   │
         │           │◄───────────────────────────────────────┤           │
         └───────────┘    Sleep Phrase / Idle Timeout / Disarm └─────┬─────┘
                                [Descending Chime]                   │
                                                                     │
                                  ┌──────────────────────────────────┴──────────────────────────────────┐
                                  │                                                                     │
                                  ▼                                                                     ▼
                        Addressed Utterance                                                     Abort Phrase
                     ("Daimon, ..." / "... Daimon")                                     ("stop", "cancel that", etc.)
                                  │                                                                     │
                                  ▼                                                                     ▼
                            Stream to Cloud                                                     Interrupt Audio
                         (Groq / Gemini / STT)                                                (Stay in AWAKE state)
```

| State | Listens For | Action on Detection | Notes |
|---|---|---|---|
| **`ASLEEP`** | "Awaken" only (standalone utterance) | Transition to `AWAKE`, play ascending chime, glow visualizer orb | All non-wake audio is dropped on-device; zero cloud calls |
| **`AWAKE`** | Addressed utterance ("Daimon" at start or end) | Stream finalized audio buffer to STT/LLM pipeline | Unaddressed speech ("Hey Rahul...", side-talk) dropped silently on-device |
| **`AWAKE`** | Abort command ("stop", "cancel that", "never mind", "Daimon, stop") | Cut in-flight TTS immediately; cancel LLM generation; stay `AWAKE` | Does NOT close session; allows user to immediately issue next command |
| **`AWAKE`** | Sleep command ("dismissed", "that's all", "go to sleep", "Daimon, sleep") | Transition to `ASLEEP`, play descending chime, dim visualizer orb | Session closed |
| **`AWAKE`** | Idle timeout | Transition to `ASLEEP` silently | Timeout duration to be empirically tuned (see Open Policies) |

---

### 2. Name Addressing & Alias Resolution

- **Position Rule:** The name must appear at the **start** ("Daimon, what is twenty-five plus seventy-eight") or **end** ("what's the weather, Daimon") of the utterance.
- **Mid-sentence mentions:** Ignored on-device (e.g. "I told Daimon earlier", "Plato wrote about the daimon").
- **Double-ended mentions:** ("Daimon, what time is it, Daimon") route exactly once.
- **Alias Map Source:** The phonetic aliases for Daimon (e.g., Damon, Dayman, Demon) must be derived empirically from the raw STT outputs of the Section E name-capture clips (`alias_map_candidates.json`), not from developer guesses. The final alias map requires explicit owner approval.
- **TTS Normalization:** Spoken output always pronounces DAY-mon (`respell_for_tts` with `TTS_NAME_RESPELL=Daymon`).

---

### 3. Acceptance Criteria & Benchmark Gates (Pre-Determined)

These metrics must be met before ADR-004 can transition from **Proposed** to **Accepted**:

| Layer / Metric | Measured On | Target Threshold | Statistical Method |
|---|---|---|---|
| **Wake True Positive Rate** | Section A (settled clips: Q, D, N) | $\ge 95\%$ | Evaluated across all test-split takes |
| **Wake False Accept Rate** | Continuous negative audio + Section B | $< 0.1\text{ per hour}$ | Rule of Three: requires $\ge 30\text{ hours}$ of zero-false-accept audio to claim $< 0.1$/hr at 95% confidence |
| **Wake False Reject Rate** | Section A (settled items) | $< 3\%$ | Quiet and desk environments |
| **Wake-to-Chime Latency** | Local hardware measurement | $< 500\text{ ms}$ p50 | Time from end of "Awaken" speech to local audio chime |
| **Name Gate Pass Rate** | Section C, E, I addressed items | $\ge 95\%$ | Routed to cloud pipeline |
| **Name Gate False Accept** | Section D, F, G (side-talk, confusables) | Minimal / Documented | Confusable names (Damon, Dayman) logged as known risks |

---

### 4. Open Policy Decisions (To Be Settled Before Implementation)

The following behaviors are recorded in the corpus as `policy_status: open` and are informational until the owner decides:

1. **One-breath Wake + Command:** ("Awaken, Daimon, what time is it" — `wake_28-30`):
   - *Option A:* Open session AND route command immediately in one turn.
   - *Option B:* Open session with chime; require second utterance for command.
2. **Carrier Prefix:** ("Hey Daimon, what's the date" — `edge_08`):
   - *Option A:* Allow carrier prefix "Hey" as a valid start boundary.
   - *Option B:* Strict name-only prefix.
3. **Bare Name in Sleep:** ("Daimon" spoken while `ASLEEP`):
   - *Option A:* Ignore completely (must say "Awaken" first).
   - *Option B:* Optional shortcut wake word in user settings (Profile B consideration).
4. **Name Alone while Awake:** ("Daimon." / "Daimon?" — `edge_01-02`):
   - *Option A:* Attention call with brief chime only.
   - *Option B:* Spoken acknowledgment ("Yes?", "Listening.").
5. **Idle Timeout Duration:**
   - Default proposal: 30 seconds of silence before descending chime and sleep.

---

### 5. On-Device Engine Selection (Deferred)

The on-device keyword engine will be selected during Phase 1b:
- **Web Client:** WebAssembly / Web Audio Worker running an on-device keyword spotting ONNX model (e.g. openWakeWord WASM, Porcupine WASM, or micro-Whisper). Must run with zero cloud calls.
- **Native / Desktop:** In-process Silero/openWakeWord CPU thread.

---

## Consequences

- Zero cloud calls occur for private room conversations, TV noise, or side-talk while asleep or awake.
- The alias map is grounded in empirical transcription data rather than speculation.
- Phase 1 remains strictly focused on web client, barge-in, and provider bake-off; wake word logic is deferred cleanly to Phase 1b.
