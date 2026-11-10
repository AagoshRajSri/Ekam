# Live End-to-End Test & Barge-In Measurement Protocol

This protocol guides the project owner through manual live verification of the Web Client, Visualizer Orb, Transcript Feed, Telemetry Logging, and End-to-End Barge-In Latency.

> [!IMPORTANT]
> **Headphones First:** Always conduct the primary barge-in measurement wearing headphones. This isolates the microphone from speaker bleed and measures true agent cut-off latency without acoustic echo cancellation artifacts.

---

## 1. Setup & Environment

1. **Start the Voice Agent Worker:**
   ```powershell
   uv run --directory services/agent python agent.py dev
   ```
2. **Start the Next.js Web App:**
   ```powershell
   pnpm --filter @ekam/web dev
   ```
3. Open `http://localhost:3000` in Google Chrome or Edge.
4. Open **Audacity** on Windows:
   - Audio Host: **Windows WASAPI**
   - Recording Device: Microphone (Headset Mic) or Stereo Mix loopback.
   - Project Rate: 48000 Hz or 44100 Hz, 16-bit mono.

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
  - Verify each turn logs a `client_telemetry` event with `first_audio_ms`.
  - Baseline to record: `first_audio_ms` (engineering reference target: ~1200 ms). Record actual observed latency.

---

## 3. End-to-End Barge-In Measurement (10 Trials)

End-to-end barge-in measures the elapsed time from the instant the user begins speaking an interruption to the instant the speakers go completely silent (audio buffers drained, WebRTC track muted, TTS cancelled).
Thresholds below are empirical baselines to record for comparison, not rigid pass/fail rejection criteria.

### Procedure:
1. Start recording in Audacity (both user microphone and system audio loopback).
2. Ask the assistant a question that provokes a multi-sentence answer:
   > *"Daimon, describe the history of Tokyo in three sentences."*
3. While the assistant is actively speaking (about 2 seconds in), speak a crisp abort command:
   > *"Stop."* or *"Daimon, stop."*
4. In Audacity:
   - Identify Point A: The initial onset of the user's voice saying "Stop".
   - Identify Point B: The exact sample where the agent's synthesized speech abruptly drops to silence.
   - Measure the duration between Point A and Point B in milliseconds ($\Delta t = B - A$).
5. Repeat for 10 trials.

### Recording Template:

| Trial | Environment | Headset / Speaker | Interrupt Onset (A) | Agent Silence (B) | Measured Latency ($\Delta t$) | Recorded Baseline |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | Q (Quiet) | Headphones | | | ms | Baseline recorded |
| 2 | Q (Quiet) | Headphones | | | ms | Baseline recorded |
| 3 | Q (Quiet) | Headphones | | | ms | Baseline recorded |
| 4 | Q (Quiet) | Headphones | | | ms | Baseline recorded |
| 5 | Q (Quiet) | Headphones | | | ms | Baseline recorded |
| 6 | Q (Quiet) | Headphones | | | ms | Baseline recorded |
| 7 | Q (Quiet) | Headphones | | | ms | Baseline recorded |
| 8 | Q (Quiet) | Headphones | | | ms | Baseline recorded |
| 9 | Q (Quiet) | Headphones | | | ms | Baseline recorded |
| 10 | Q (Quiet) | Headphones | | | ms | Baseline recorded |

### Aggregate Statistics:
- **Median (p50):** `___ ms` (Recorded baseline; reference target: ~250 ms)
- **95th Percentile (p95):** `___ ms` (Recorded baseline; reference target: ~300 ms)
- **Worst Case:** `___ ms` (Alarm / investigation threshold: > 400 ms)

---

## 4. Speaker Bleed & Echo Cancellation Test (5 Trials)

Repeat the test without headphones, using laptop speakers at comfortable volume:
1. Speak command -> Agent begins replying through speakers.
2. User interrupts with: *"Cancel that."*
3. Verify whether browser Acoustic Echo Cancellation (AEC) allows the interruption to be detected through the ongoing speaker output.
4. Record observed latency and note any false barge-in triggers or audio ducking.

---

## 5. Logging Results in `docs/STATUS.md`

Once measured, record the aggregate numbers under Section 1 of `docs/STATUS.md`:

```markdown
- [x] End-to-end barge-in measured in a live session (2026-11-XX):
  - Headphones: p50 = XXX ms, p95 = YYY ms, worst = ZZZ ms (10 trials).
  - Target: <= 300 ms. Status: PASS / ELEVATED.
  - Speaker loopback: 5 trials, AEC settling confirmed.
```
