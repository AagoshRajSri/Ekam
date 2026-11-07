# Benchmark Corpus Recording Guide (Phase 0 / P0-7)

> **Mandatory Milestone Gate:** Per `BABY_ROADMAP.md` and `AGENTS.md`, **Step 5 (Provider bake-off) and the Phase 1 exit criteria are BLOCKED** until this corpus is physically recorded and transcripts are validated.

Record **50–100 short audio files** (.wav, 16 kHz mono) of yourself speaking. Store the audio files in `evals/corpus/wavs/` and map them to their exact ground-truth transcripts in `evals/corpus/ground_truth.json`.

---

## 1. Recording Setup & Environments
- **Format:** 16,000 Hz (16 kHz), 16-bit PCM, Mono WAV.
- **Microphone & Environments:**
  - **Quiet room (Headset/Mic):** 30 utterances
  - **Speakerphone / Laptop built-in mic (1 meter away):** 15 utterances
  - **Noisy room (Fan, background music, or cafeteria chatter):** 15 utterances

---

## 2. Benchmark Utterance Catalog

### A. Tier 0: Math, Control, Time (10 items)
1. `stop`
2. `cancel that`
3. `be quiet`
4. `never mind`
5. `what is twenty-five plus seventy-eight`
6. `what's two hundred seventy-three times four hundred ninety-one`
7. `what is fifteen percent of two thousand four hundred`
8. `convert fifty miles to kilometers`
9. `what is eighty degrees fahrenheit in celsius`
10. `what time is it in Tokyo right now`

### B. Context & Conversation (5 items)
11. `what's the weather in Mumbai`
12. `what about tomorrow`
13. `will it rain this evening`
14. `tell me a one sentence joke`
15. `who won the cricket world cup in 2011`

### C. Contact Names & Messaging (Entity WER Test) (5 items)
16. `text Rahul I'm reaching in ten minutes`
17. `call Rohan`
18. `no, call Rahul Sharma`
19. `send an email to Priya saying the deck is ready`
20. `message Vikram on WhatsApp`

### D. Corrections & Ambiguity (3 items)
21. `set a timer for fifteen minutes... actually make it twenty minutes`
22. `remind me to carry an umbrella at eight AM`
23. `cancel the umbrella reminder`

### E. Hindi / Code-Mixed Utterances (Unscored Baseline) (10 items)
24. `aaj ka mausam kaisa hai`
25. `kal barish hogi kya`
26. `Rahul ko message bhejo ki main dus minute mein pahunch raha hoon`
27. `ek cup chai banane ka timer laga do`
28. `mujhe aath baje jagana`
29. `kya tum Hindi samajhte ho`
30. `meeting kab schedule hui hai`
31. `aaj traffic kaisa hai`
32. `Delhi ka temperature kitna hai`
33. `gaane play karo`

### F. Wake Word Repetitions (~20 reps of "Ekam")
34–53. Record **20 repetitions** saying **"Ekam"**:
  - Reps 34–40: Normal conversational tone (quiet room)
  - Reps 41–46: Quick / clipped command tone (e.g., "Ekam, stop")
  - Reps 47–50: Across the room / speakerphone
  - Reps 51–53: Background noise active (fan/music)

---

## 3. Ground Truth JSON Structure

Save in `evals/corpus/ground_truth.json`:
```json
{
  "utterance_01.wav": {
    "text": "stop",
    "tier": 0,
    "environment": "quiet_headset",
    "expected_action": "abort"
  },
  "utterance_34.wav": {
    "text": "Ekam",
    "type": "wake_word",
    "environment": "quiet"
  }
}
```
