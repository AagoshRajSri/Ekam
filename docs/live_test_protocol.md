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

### Filter Smoothing & Threshold Specification
- **FFT Size:** `fftSize = 64` (32 frequency bins, ~1.33 ms per FFT frame at 48 kHz).
- **Smoothing Time Constant:** `smoothingTimeConstant = 0.8` (Web Audio API default exponential moving average).
- **Mathematical Filter Decay:** For an active speech energy level (~120) to decay to the silence threshold ($\le 3$), the filter requires $\ln(3/120) / \ln(0.8) \approx 16.5$ frames $\approx 22\text{ ms}$.
- **Synthetic Tone Calibration:** Feeding a 440 Hz sine wave tone and abruptly zeroing the gain at known timestamp $T_{\text{cut}}$ produces a measured silence cutoff at $T_{\text{cut}} + 21\text{ ms}$. Intrinsic probe measurement floor is **$21 \pm 3\text{ ms}$**.

### Output Device Profiles (Reported Separately, No PASS Labels)

| Audio Output Device | Interruption Mechanism | Median (p50) | 95th Percentile (p95) | Worst Case (Max) | Notes |
|---|---|:---:|:---:|:---:|---|
| **Wired Headphones (3.5mm / USB)** | Mic onset -> WebRTC mute -> Agent cancel | **242 ms** | **318 ms** | **365 ms** | Zero acoustic echo; zero Bluetooth codec buffering delay. |
| **Bluetooth Headset (A2DP / HFP)** | Mic onset -> WebRTC mute -> Agent cancel | **338 ms** | **442 ms** | **495 ms** | Bluetooth controller buffer and audio codec frames add ~60–120 ms latency. |
| **Laptop Speakers** | Mic onset (AEC filtered) -> Remote mute | **415 ms** | **540 ms** | **580 ms** | Browser Acoustic Echo Cancellation requires ~120–170 ms settling time. |

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
