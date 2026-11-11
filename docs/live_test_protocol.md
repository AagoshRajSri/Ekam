# Live End-to-End Test & Barge-In Measurement Protocol

This protocol guides the project owner through live verification of the Web Client, Visualizer Orb, Transcript Feed, Telemetry Logging, and End-to-End Barge-In Latency.

> [!NOTE]
> **No Audacity or Two-Device Setup Required:** The web client now features an integrated real-time Client-Side Barge-In Probe (`VoiceRoom.tsx`). It measures speech onset on the user's microphone against the abrupt silence cutoff on the remote WebRTC audio track using Web Audio API analysers. Live measurements appear immediately in the Telemetry Bar badge and persist to `services/agent/telemetry_traces.jsonl`.

---

## 1. Setup & Environment

1. **Start the Voice Agent Worker:**
   ```powershell
   uv run --project services/agent python agent.py dev
   ```
2. **Start the Next.js Web App:**
   ```powershell
   pnpm dev:web
   # (or: pnpm --filter @daimon/web dev)
   ```
3. Open `http://localhost:3000` in Google Chrome or Edge.
4. Open browser DevTools console (F12) to observe live telemetry packets if desired.

---

## 2. Visual & Telemetry Verification Check

Connect to the room by clicking **Connect**:

- [ ] **Visualizer Orb States:**
  - `LISTENING`: Subtle slow cyan/blue breathing pulse while idle.
  - `THINKING`: Rapid violet/purple orbit animation during LLM generation.
  - `SPEAKING`: Dynamic amber/gold waveform modulation driven by agent audio volume.
- [ ] **Live Transcript Feed:**
  - Speak: *"Hello, what time is it?"*
  - Verify your utterance appears in the transcript feed.
  - Verify the agent's reply appears in the transcript feed.
- [ ] **Telemetry Logging:**
  - Inspect `services/agent/telemetry_traces.jsonl` in PowerShell:
    ```powershell
    Get-Content services/agent/telemetry_traces.jsonl -Tail 5
    ```
  - Verify each turn logs a `client_turn_telemetry` event with `first_audio_ms`, `stt_requests`, `llm_requests`, and `tts_requests`.

---

## 3. End-to-End Barge-In Measurement (In-Client Probe)

The client probe attaches two `AnalyserNode` instances:
- **Mic Analyser:** Detects user speech energy onset (> 16) while the agent is speaking (> 8).
- **Remote Track Analyser:** Detects the moment remote synthesized audio drops to silence (<= 3).
- **Reported Metric:** Real elapsed $\Delta t$ between user speech onset and remote silence.

### Procedure (10 Trials Headphones, 10 Trials Speakers):
1. Wear headphones (for trial set 1) or switch to laptop speakers (for trial set 2).
2. Prompt the assistant to speak continuously:
   > *"Can you spell A to Z?"* or *"Count from one to twenty."*
3. While the assistant is actively speaking, speak a crisp abort command:
   > *"Stop."*, *"Cancel that."*, or *"Never mind."*
4. Confirm:
   - The agent ceases speaking immediately (not waiting for false-interruption timers).
   - The Telemetry Bar updates with `Barge-In: <ms> (N trials)`.
   - The JSONL log records `client_barge_in_telemetry`.
5. Repeat for 10 trials with headphones and 10 trials on speakers.

### Recording Template:

| Trial | Environment | Output Device | User Interrupt Command | Measured Latency ($\Delta t$) | Trace Event |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | Quiet | Headphones | "Stop." | ms | logged |
| 2 | Quiet | Headphones | "Stop." | ms | logged |
| 3 | Quiet | Headphones | "Cancel that." | ms | logged |
| 4 | Quiet | Headphones | "Stop." | ms | logged |
| 5 | Quiet | Headphones | "Never mind." | ms | logged |
| 6 | Quiet | Headphones | "Stop." | ms | logged |
| 7 | Quiet | Headphones | "Cancel." | ms | logged |
| 8 | Quiet | Headphones | "Stop." | ms | logged |
| 9 | Quiet | Headphones | "Stop." | ms | logged |
| 10 | Quiet | Headphones | "Cancel that." | ms | logged |

---

## 4. Speaker Bleed & Echo Cancellation Test (10 Trials)

Repeat the test without headphones, using laptop speakers at a comfortable listening volume:
1. Speak command: *"Count to twenty slowly."* -> Agent begins replying through speakers.
2. User interrupts with: *"Stop."* or *"Cancel that."*
3. The browser Acoustic Echo Cancellation (AEC) cancels the agent's speaker output from the mic stream, isolating the user's interruption voice.
4. The client probe detects interruption onset and records the duration until remote audio ceases.
5. Record 10 trials to evaluate AEC latency overhead compared to headphones.

---

## 5. Aggregate Telemetry Analysis & Reporting

Inspect logged barge-in trials from `telemetry_traces.jsonl`:
```powershell
Get-Content services/agent/telemetry_traces.jsonl | Select-String "client_barge_in_telemetry"
```

Compute aggregate statistics:
- **Headphones (10 trials):** Median (p50) and Worst Case (max).
- **Speakers (10 trials):** Median (p50) and Worst Case (max).

Record the measured numbers under Phase 1 Telemetry in `docs/STATUS.md`.
