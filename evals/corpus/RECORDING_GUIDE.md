# Benchmark Corpus Recording Guide (Phase 0 / Phase 1)

> **Mandatory Milestone Gate:** Per `BABY_ROADMAP.md` and `docs/STATUS.md`, **Step 5 (Provider bake-off) and the Phase 1 exit criteria are BLOCKED** until this corpus is physically recorded and transcripts are validated.

Record short audio files (`.wav`, 16 kHz mono) of yourself speaking. Store the audio files in `evals/corpus/wavs/` and map them to their exact ground-truth transcripts in `evals/corpus/ground_truth.json`.

---

## 1. System Architecture & Trigger Protocols

Ekam / Daimon operates under a **Modal Voice Architecture**:

1. **Session Gate ("Awaken"):**
   - Said as an **isolated, standalone word** framed by a brief pause before and after (`[silence] → "Awaken." → [silence]`).
   - Flips the session state from `ASLEEP` to `AWAKE`.
   - Plays a wake chime and triggers the visualizer Orb glow.
2. **Per-Request Addressing ("Daimon"):**
   - While `AWAKE`, every command is addressed using the name at the **start or end** of the sentence (e.g., *"Daimon, check my email"* or *"What's the weather, Daimon?"*).
   - Accepted aliases: `Daimon`, `Damon`, `Dayman`, `Demon`.
3. **Session Sleep / Exit:**
   - Verbal bailouts: `"dismissed"`, `"that's all"`, `"Daimon, sleep"`, `"go to sleep"`.
   - Transitions session back to `ASLEEP` with a gentle descending chime.
4. **Side-Talk & False Trigger Rejection (Negative Controls):**
   - Utterances spoken without "Daimon" during an open session must be **ignored** (dropped before calling cloud LLM).
   - "Awaken" embedded in natural conversation (e.g. *"I need to awaken early tomorrow"*) must **not** trigger session wake.

---

## 2. Recording Specifications

- **Format:** 16,000 Hz (16 kHz), 16-bit PCM, Mono WAV (`.wav`).
- **Target Environments:**
  - **Quiet room (Headset or close mic):** Baseline clarity
  - **Speakerphone / Laptop built-in mic (1–2 meters away):** Real-world desk use
  - **Noisy environment (Fan, background music, or TV running):** Noise robustness

---

## 3. Utterance Recording Catalog

### A. Wake Session Triggers: "Awaken" (15 items)
*Goal: Measure True Positive Rate (TPR) on isolated "Awaken" across acoustics.*

| ID | Spoken Text | Environment / Delivery | Expected Result |
|---|---|---|---|
| `wake_01`–`wake_05` | `"Awaken."` | Quiet room, natural pace (0.5s pause before & after) | Open session |
| `wake_06`–`wake_08` | `"Awaken."` | Quick, clipped / whisper / tired tone | Open session |
| `wake_09`–`wake_11` | `"Awaken."` | Laptop mic, 2 meters away (speakerphone distance) | Open session |
| `wake_12`–`wake_15` | `"Awaken."` | Background noise active (fan / ambient music) | Open session |

---

### B. Wake Rejection Controls: Embedded "Awaken" (5 items)
*Goal: Verify VAD silence-framing prevents accidental wakes during conversation.*

| ID | Spoken Text | Expected Result |
|---|---|---|
| `wake_neg_01` | `"I have to awaken early tomorrow morning"` | Ignore / Stay Asleep |
| `wake_neg_02` | `"the coffee helped awaken my senses"` | Ignore / Stay Asleep |
| `wake_neg_03` | `"will you awaken them when they arrive"` | Ignore / Stay Asleep |
| `wake_neg_04` | `"an awakening experience for the team"` | Ignore / Stay Asleep |
| `wake_neg_05` | `"awakenings happen naturally"` | Ignore / Stay Asleep |

---

### C. Addressed Commands: "Daimon" & Aliases (15 items)
*Goal: Benchmark STT Word Error Rate (WER) and ensure the name gate passes the command to the LLM.*

| ID | Spoken Text | Category |
|---|---|---|
| `cmd_01` | `"Daimon, what time is it in Tokyo right now"` | Time / Math |
| `cmd_02` | `"Daimon, what is twenty-five plus seventy-eight"` | Tier 0 Math |
| `cmd_03` | `"what is fifteen percent of two thousand four hundred, Daimon"` | Tail-addressed |
| `cmd_04` | `"convert fifty miles to kilometers, Daimon"` | Tail-addressed |
| `cmd_05` | `"Daimon, what's the weather in Mumbai"` | Context / Weather |
| `cmd_06` | `"will it rain this evening, Daimon"` | Weather follow-up |
| `cmd_07` | `"Daimon, tell me a one sentence joke"` | Conversational |
| `cmd_08` | `"Daimon, text Rahul I'm reaching in ten minutes"` | Messaging / Indian entity |
| `cmd_09` | `"call Rohan, Daimon"` | Contact entity |
| `cmd_10` | `"Daimon, send an email to Priya saying the deck is ready"` | Messaging entity |
| `cmd_11` | `"set a timer for fifteen minutes, Daimon"` | Timer |
| `cmd_12` | `"Damon, what's on my calendar today"` | Alias: Damon |
| `cmd_13` | `"Dayman, summarize my unread messages"` | Alias: Dayman |
| `cmd_14` | `"Demon, check git status"` | Alias: Demon |
| `cmd_15` | `"Daimon, remind me to carry an umbrella at eight AM"` | Reminder |

---

### D. Side-Talk Rejection: Speech WITHOUT Name (8 items)
*Goal: Verify speech heard while AWAKE that does NOT contain "Daimon" is dropped without calling cloud LLM.*

| ID | Spoken Text | Expected Action |
|---|---|---|
| `sidetalk_01` | `"Hey Rahul, did you order the food?"` | Silent drop (No LLM call) |
| `sidetalk_02` | `"Can you pass me the water bottle?"` | Silent drop (No LLM call) |
| `sidetalk_03` | `"Yeah, I think the meeting starts at three."` | Silent drop (No LLM call) |
| `sidetalk_04` | `"Where did I leave my keys?"` | Silent drop (No LLM call) |
| `sidetalk_05` | `"Excuse me, what time does the shop close?"` | Silent drop (No LLM call) |
| `sidetalk_06` | `"Look at this new design on the screen."` | Silent drop (No LLM call) |
| `sidetalk_07` | `"Yes, absolutely."` | Silent drop (No LLM call) |
| `sidetalk_08` | `"Turn off the fan, please."` *(Said to someone else)* | Silent drop (No LLM call) |

---

### E. Session Sleep & Bailout Triggers (10 items)
*Goal: Benchmark instant local session close triggers.*

| ID | Spoken Text | Expected Action |
|---|---|---|
| `sleep_01` | `"dismissed"` | Close session $\to$ ASLEEP |
| `sleep_02` | `"that's all"` | Close session $\to$ ASLEEP |
| `sleep_03` | `"that's all, Daimon"` | Close session $\to$ ASLEEP |
| `sleep_04` | `"Daimon, go to sleep"` | Close session $\to$ ASLEEP |
| `sleep_05` | `"Daimon, sleep"` | Close session $\to$ ASLEEP |
| `sleep_06` | `"stop"` | Immediate cutoff $\to$ ASLEEP |
| `sleep_07` | `"be quiet"` | Immediate cutoff $\to$ ASLEEP |
| `sleep_08` | `"cancel that"` | Abort action $\to$ ASLEEP |
| `sleep_09` | `"never mind"` | Cancel $\to$ ASLEEP |
| `sleep_10` | `"thanks, Daimon, that's all for now"` | Close session $\to$ ASLEEP |

---

### F. Hindi & Code-Mixed Utterances (Unscored Baseline) (10 items)
*Goal: Benchmark Whisper multilingual accuracy on Indian English / Hinglish.*

| ID | Spoken Text | Meaning |
|---|---|---|
| `hi_01` | `"Daimon, aaj ka mausam kaisa hai"` | Weather query |
| `hi_02` | `"kal barish hogi kya, Daimon"` | Rain query |
| `hi_03` | `"Daimon, Rahul ko message bhejo ki main dus minute mein pahunch raha hoon"` | Messaging |
| `hi_04` | `"ek cup chai banane ka timer laga do, Daimon"` | Timer |
| `hi_05` | `"Daimon, mujhe aath baje jagana"` | Alarm / reminder |
| `hi_06` | `"kya tum Hindi samajhte ho, Daimon"` | Language check |
| `hi_07` | `"Daimon, meeting kab schedule hui hai"` | Calendar check |
| `hi_08` | `"aaj traffic kaisa hai, Daimon"` | Traffic query |
| `hi_09` | `"Daimon, Delhi ka temperature kitna hai"` | City temperature |
| `hi_10` | `"gaane play karo, Daimon"` | Media play |

---

## 4. Ground Truth Mapping Schema

Save mappings in `evals/corpus/ground_truth.json`:

```json
{
  "wake_01.wav": {
    "text": "Awaken",
    "type": "session_wake",
    "environment": "quiet_headset",
    "expected_action": "open_session"
  },
  "wake_neg_01.wav": {
    "text": "I have to awaken early tomorrow morning",
    "type": "wake_negative_control",
    "environment": "quiet_headset",
    "expected_action": "ignore"
  },
  "cmd_01.wav": {
    "text": "Daimon, what time is it in Tokyo right now",
    "type": "addressed_command",
    "name_present": true,
    "alias_used": "Daimon",
    "expected_action": "route_to_llm"
  },
  "sidetalk_01.wav": {
    "text": "Hey Rahul, did you order the food?",
    "type": "side_talk_control",
    "name_present": false,
    "expected_action": "silent_drop"
  },
  "sleep_01.wav": {
    "text": "dismissed",
    "type": "session_sleep",
    "expected_action": "close_session"
  }
}
```

---

## 5. Summary Total Count

| Category | Purpose | Count |
|---|---|:---:|
| **A. Wake Triggers ("Awaken")** | Session activation across distances & noise | 15 |
| **B. Wake Negative Controls** | VAD framing / conversational embedding rejection | 5 |
| **C. Addressed Commands** | WER, Math, Weather, Indian Entities, Aliases | 15 |
| **D. Side-Talk Rejection** | Zero-call rejection when name is absent | 8 |
| **E. Session Sleep & Bailouts** | Instant close (`dismissed`, `that's all`, etc.) | 10 |
| **F. Hindi / Code-Mixed** | Multilingual & regional phonetic baseline | 10 |
| **Total** | Full empirical coverage for Phase 1 / Step 5 | **63 WAVs** |
