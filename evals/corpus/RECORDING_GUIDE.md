# Benchmark Corpus Recording Guide (Phase 0 / P0-7)

To satisfy the exit criteria for Phase 0 and establish your latency and accuracy baseline, record **50–100 short audio files** (.wav, 16 kHz mono) of yourself speaking.

Store the audio files in `evals/corpus/wavs/` and map them to their exact ground-truth transcripts in `evals/corpus/ground_truth.json`.

---

## 1. Recording Setup
- **Sample Rate:** 16,000 Hz (16 kHz), 16-bit PCM, Mono.
- **Environments:**
  - 30 utterances: Quiet room, headset/headphones.
  - 15 utterances: Laptop built-in microphone on desk (speakerphone mode).
  - 15 utterances: Room with background noise (fan, TV, or music playing softly).

---

## 2. Recommended Test Utterance Categories

### Tier 0 (Math, Control, Time)
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

### Context & Conversation (Tier 1)
11. `what's the weather in Mumbai`
12. `what about tomorrow`
13. `will it rain this evening`
14. `tell me a one sentence joke`
15. `who won the cricket world cup in 2011`

### Contact Names & Messaging (Entity WER Test)
16. `text Rahul I'm reaching in ten minutes`
17. `call Rohan`
18. `no, call Rahul Sharma`
19. `send an email to Priya saying the deck is ready`
20. `message Vikram on WhatsApp`

### Corrections & Ambiguity
21. `set a timer for fifteen minutes... actually make it twenty minutes`
22. `remind me to carry an umbrella at eight AM`
23. `cancel the umbrella reminder`

