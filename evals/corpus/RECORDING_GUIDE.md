# Daimon Benchmark Corpus Recording Guide (v2)

Comprehensive operational guide and protocol for capturing, validating, and deriving the Daimon voice benchmark corpus across quiet (Q), desk distance (D), and noisy (N) environments.

- **Copy-paste Command Reference:** All execution commands are documented in [`evals/corpus/COMMANDS.md`](COMMANDS.md). Every command is runnable copy-paste from the repository root.
- **Recording Script:** Pre-ordered interactive checklist scripts are generated at [`RECORDING_SCRIPT.md`](RECORDING_SCRIPT.md) and [`RECORDING_SCRIPT.csv`](RECORDING_SCRIPT.csv).

1. Design under test (v1.1)
State	Listens for	Notes
ASLEEP	“Awaken” only, said as a standalone utterance	Everything else is dropped on-device
AWAKE	“Daimon” (aliases: Damon, Dayman, Demon) at the start or end of an utterance	Speech without the name is dropped before any cloud call
Abort (stays AWAKE)	“stop” (during TTS), “cancel that”, “never mind”, “Daimon, stop”	Cancels the current request or speech only
Sleep (to ASLEEP)	“dismissed”, “that’s all”, “go to sleep”, “Daimon, sleep”, and tail or combined forms	Gentle descending chime

Decision note: “Stop”, “cancel that”, and “never mind” are classified as abort-only (stays AWAKE) rather than closing the session, because those phrases convey "drop this request" or "interrupt current speech", not "go to sleep".

Policy items still open. The corpus records them, but the expected action is TBD and the result is informational until resolved:

“Awaken” followed directly by a command in one breath
“Hey Daimon, ...” (a carrier prefix)
“Awaken” with a short pause or right after other speech

2. Recording specifications
Capture: 48 kHz, 24-bit or 16-bit mono WAV, with AGC, noise suppression and echo cancellation turned OFF. Keep these masters in `evals/corpus/masters/`.
Derive: 16 kHz, 16-bit mono WAV for the pipeline (`evals/corpus/wavs/`). Derived automatically using the polyphase resampler in `check_corpus.py derive`. Keep originals intact.
Levels: peaks between about -18 and -3 dBFS (nominal target -12 to -6 dBFS), zero digital clipping. Record about 1 s of lead and trail room tone before and after each clip.
Environments (code in the filename):
Code	Setup
Q	Quiet room: wired headset or close microphone (15–20 cm)
D	Desk: laptop built-in mic, you sit 1–2 m away from the laptop (distance speech; not a loudspeaker)
N	Noisy: fan, background music, or TV running at a realistic, fixed volume level
Takes: 2 takes per item. Don’t delete “bad” takes. Mark technical faults in `evals/corpus/quality_flags.json`.
Filename: {speaker}_{env}_{id}_t{take}.wav, for example `s01_Q_cmd_01_t1.wav`.
Dev/test split: sealed in `evals/corpus/split.lock` (152 dev clips / 102 test clips). Deterministic split by item.

### Name Pronunciation & Delivery Rules
- **"Daimon" (primary assistant name):** Pronounced **DAY-mon** (/ˈdeɪmɒn/) across all lines in the catalog, **except** items `name_31–40`.
- **`name_31–40` (phonetic variant):** Deliberately pronounced **DY-mon** (/ˈdaɪmɒn/) to benchmark variant STT transcription.
- **"Damon" (cmd_12, conf_01, conf_02):** Pronounced **DAY-mun** (/ˈdeɪmən/).
- **"Dayman" (cmd_13, conf_08):** Pronounced **DAY-man** (/ˈdeɪmæn/).
- **"Demon" (cmd_14, conf_07, conf_09):** Pronounced **DEE-mon** (/ˈdiːmən/).
  *(Ensures the alias recordings sound distinctly different from the primary name).*
- **Section G (Side-talk while AWAKE):** Speak each line to an imaginary person next to you in the room, turning slightly away rather than projecting directly into the microphone.

### Hardware & Acoustic Consistency
- **Microphone Selection:**
  - Use one consistent microphone for the entire **Block Q** (wired headset or close USB/XLR mic).
  - Switch to the laptop's built-in microphone for **Block D** (Distance).
  - Note the exact device names used, as the ground-truth metadata records the `device` field.
- **Noise Consistency (Block N):**
  - Keep the background noise source (fan, radio, TV) at a constant, fixed volume level throughout the entire N block.

### Windows 48 kHz Recording Setup Checklist
Before starting a recording session on Windows:
1. **Audio Format (48 kHz 24-bit/16-bit):**
   - Press `Win + R`, type `mmsys.cpl` (or open Windows Sound Settings $\to$ More sound settings).
   - Go to the **Recording** tab, select your input microphone, and click **Properties**.
   - Navigate to the **Advanced** tab.
   - Under **Default Format**, select: **2-channel or 1-channel, 24-bit or 16-bit, 48000 Hz (Studio Quality)**.
2. **Turn OFF Enhancements, AGC & Noise Suppression:**
   - In the same Properties dialog, go to **Enhancements** (if present) and check **Disable all enhancements**.
   - If using OEM audio software (Realtek Audio Console, Waves MaxxAudio Pro, Dell Optimizer, HP Audio Center, Lenovo Vantage, Nahimic), open that control panel and turn OFF all microphone effects: disable "Acoustic Echo Cancellation", "Noise Suppression", "Voice Clarity", "Auto Gain Control / AGC", and "Conference Mode".
3. **NO Bluetooth Microphones:**
   - **Do NOT record with Bluetooth headsets or earbuds** (e.g. AirPods, Sony WH/WF, Galaxy Buds). Bluetooth Hands-Free Profile (HFP) drops microphone sampling to 8 kHz or 16 kHz (mSBC/CVSD codec) with extreme dynamic compression and clipping artifacts. Use a USB microphone, XLR audio interface, or analog 3.5mm headset.
4. **Close Interfering Applications:**
   - Close Discord, Microsoft Teams, Zoom, Slack, Skype, and all browser tabs with microphone access to prevent background audio ducking or stream hijacking.
5. **Acoustic Consistency:**
   - Maintain consistent microphone distance (15–20 cm / 6–8 inches for Block Q; use a pop filter if available).
   - Lock physical mic gain and Windows recording level slider once set; do not adjust between takes.

### Recommended Recording Order
Follow the pre-generated interactive scripts in [`RECORDING_SCRIPT.md`](RECORDING_SCRIPT.md):
1. **Block Q (Quiet Room — 146 clips):**
   - Record in order: **Section C** (Commands) $\to$ **Section E** (Name pronunciations) $\to$ **Section I** (Hindi/Hinglish) $\to$ **Section G** (Side-talk negatives) $\to$ **Section A** (Awaken wake words).
   - This records the core conversational and command lines first while vocal energy is fresh, followed by bilingual phrasing, side-talk, and isolated wake words.
2. **Block D (Desk / Distance — 50 clips):**
   - Re-record Section C items 16–25 (20 clips), Section E items 11–20 (20 clips), and wake_06–10 (10 clips).
3. **Block N (Noisy Environment — 58 clips):**
   - Re-record with fan / background media running: Section C items 26–35 (20 clips), Section E items 21–30 (20 clips), Section G items 09–12 (8 clips), and wake_11–15 (10 clips).

3. Speakers
s01 (you): records everything in sections A–I (178 items, about 356 clips at 2 takes). Note that Phase 1 focuses on the 127 bake-off items (254 clips) across sections A, C, E, G, I.
s02-s05 (at least 3, ideally 4 others): each records the speaker subset (45 items): wake_01-10, wake_neg_01-05, cmd_01-15, name_01-10, sleep_01-05. Include different genders, ages and accents, and at least two with strongly Indian-English speech patterns. Record their metadata (self-described accent or L1, device) with consent.
If you can’t recruit others, label every result “single-speaker baseline” and don’t generalize.

4. Utterance catalog (speaker s01)

> **Bake-off corpus scope (speaker s01, sections A, C, E, G, I): exactly 127 items / 254 clips at 2 takes** (formalized in `evals/corpus/manifest.json`).
> Sections B, D, F, H (51 items / 102 clips) belong to the Phase 1b wake-word corpus and are recorded separately.
>
> **Phase 1b Note on Sections A & G:**
> Section A (*Awaken* wake-word variants) and Section G (*Side-talk while AWAKE* negative controls) primarily benchmark the on-device keyword spotting and name-gating architecture defined in **Phase 1b** (ADR-004). However, both sections are included in the Phase 1 recording manifest (127 items / 254 clips) and script so that speaker s01 can record all acoustic environments and control clips in a single sitting while the microphone setup is calibrated. In Phase 1 provider bake-off runs, the harness evaluates available pipeline clips and reports coverage gracefully without blocking on missing sections.

A. Wake “Awaken” (30 items)
ID	Spoken	Condition	Expected
wake_01-05	“Awaken.”	Q, natural pace, about 0.5 s pause before and after	Open session
wake_06-10	“Awaken.”	D, natural	Open session
wake_11-15	“Awaken.”	N, natural	Open session
wake_16-19	“Awaken.”	Whisper / clipped / tired / loud-fast (Q)	Open session
wake_20-23	“Awaken.”	Stress variants: uh-WAY-ken ×2, AW-ken-style ×2 (Q)	Open session
wake_24-25	“Awaken.”	Short pause (~0.2 s) before and after, flowing speech (Q)	Informational
wake_26-27	“okay, so... Awaken.”	Said right after other speech (Q)	Informational
wake_28-30	“Awaken, Daimon, what time is it”	One breath, with command (Q)	TBD
B. Wake negatives, embedded “awaken” (13 items)
ID	Spoken	Expected
wake_neg_01	“I have to awaken early tomorrow morning”	Stay asleep
wake_neg_02	“the coffee helped awaken my senses”	Stay asleep
wake_neg_03	“will you awaken them when they arrive”	Stay asleep
wake_neg_04	“an awakening experience for the team”	Stay asleep
wake_neg_05	“awakenings happen naturally”	Stay asleep
wake_neg_06	“please don’t awaken the baby”	Stay asleep
wake_neg_07	“it’s time to awaken him”	Stay asleep
wake_neg_08	“she will awaken soon”	Stay asleep
wake_neg_09	“Sleeping Beauty will awaken with a kiss”	Stay asleep
wake_neg_10	“Awaken them.” (hard negative: short, with an object)	Stay asleep
wake_neg_11-13	Repeats of wake_neg_01, 03, 10 in N	Stay asleep
C. Addressed commands (35 items)

Items marked ★ are re-recorded in D and N.

ID	Spoken	Category
cmd_01 ★	“Daimon, what time is it in Tokyo right now”	Time
cmd_02 ★	“Daimon, what is twenty-five plus seventy-eight”	Math
cmd_03 ★	“what is fifteen percent of two thousand four hundred, Daimon”	Tail
cmd_04	“convert fifty miles to kilometers, Daimon”	Tail
cmd_05 ★	“Daimon, what’s the weather in Mumbai”	Weather
cmd_06 ★	“will it rain this evening, Daimon”	Tail
cmd_07	“Daimon, tell me a one sentence joke”	Conversational
cmd_08 ★	“Daimon, text Rahul I’m reaching in ten minutes”	Entity
cmd_09 ★	“call Rohan, Daimon”	Entity, tail
cmd_10	“Daimon, send an email to Priya saying the deck is ready”	Entity
cmd_11 ★	“set a timer for fifteen minutes, Daimon”	Timer
cmd_12 ★	“Damon, what’s on my calendar today”	Alias
cmd_13	“Dayman, summarize my unread messages”	Alias
cmd_14	“Demon, check git status”	Alias
cmd_15 ★	“Daimon, remind me to carry an umbrella at eight AM”	Reminder
cmd_16-25	The ★ items above, recorded in D	Distance
cmd_26-35	The ★ items above, recorded in N	Noise
D. Name-position edge cases (10 items)
ID	Spoken	Expected
edge_01	“Daimon.” (name alone)	Attention call (decide: chime only or prompt)
edge_02	“Daimon?”	Same as edge_01
edge_03	“tell Daimon to check my email” (mid-sentence)	Ignore
edge_04	“I was reading about the daimon in Plato”	Ignore
edge_05	“ask Daimon what time it is”	Ignore
edge_06	“Daimon, what time is it, Daimon” (both ends)	Route once
edge_07	“um, Daimon, what’s the date” (after hesitation)	Route
edge_08	“Hey Daimon, what’s the date”	TBD (carrier prefix)
edge_09	“what’s the date, uh, Daimon” (tail with filler)	Route
edge_10	“Daimon check the time Daimon check the time” (repeat)	Route once
E. Name capture and alias map (40 items)

The goal is the list of ways STT actually writes the name.

ID	Spoken	Condition
name_01-10	“Daimon.” (DAY-mon)	Q
name_11-20	“Daimon.” (DAY-mon)	D
name_21-30	“Daimon.” (DAY-mon)	N
name_31-40	“Daimon.” (DY-mon variant)	Q

For each clip, log the raw STT output. The alias map in the pipeline should come from this data, not from guesses.

F. Confusables and known false-accept risks (10 items)

These are said to another person or in conversation. The aliases are accepted, so some of these will route to the LLM. That is a known limitation, and this section measures its size.

ID	Spoken	Expected
conf_01	“Damon, did you finish the report?”	Known risk (routes)
conf_02	“Damon, can you pass the salt”	Known risk (routes)
conf_03	“Simon, are you coming tonight”	Ignore
conf_04	“Raymond, call me back”	Ignore
conf_05	“hey man, what’s up”	Ignore
conf_06	“it’s a day, man”	Ignore
conf_07	“that movie was a demon of a film”	Ignore
conf_08	“Dayman, Dayman, Dayman”	Known risk
conf_09	“Demon Slayer is on tonight”	Ignore
conf_10	“the daemon process is running”	Ignore
G. Side-talk while AWAKE (12 items)

> **Delivery note:** Say these lines speaking to an imaginary person sitting next to you in the room, turning slightly away rather than talking straight into the microphone. These measure whether unaddressed conversation while AWAKE is silently dropped without invoking the LLM.

ID	Spoken	Condition	Expected
sidetalk_01	“Hey Rahul, did you order the food?”	Q	Silent drop
sidetalk_02	“Can you pass me the water bottle?”	Q	Silent drop
sidetalk_03	“Yeah, I think the meeting starts at three.”	Q	Silent drop
sidetalk_04	“Where did I leave my keys?”	Q	Silent drop
sidetalk_05	“Excuse me, what time does the shop close?”	Q	Silent drop
sidetalk_06	“Look at this new design on the screen.”	Q	Silent drop
sidetalk_07	“Yes, absolutely.”	Q	Silent drop
sidetalk_08	“Turn off the fan, please.”	Q	Silent drop
sidetalk_09	sidetalk_01 (“Hey Rahul, did you order the food?”)	N	Silent drop
sidetalk_10	sidetalk_03 (“Yeah, I think the meeting starts at three.”)	N	Silent drop
sidetalk_11	sidetalk_05 (“Excuse me, what time does the shop close?”)	N	Silent drop
sidetalk_12	sidetalk_08 (“Turn off the fan, please.”)	N	Silent drop
H. Sleep, abort and near-miss controls (18 items)
ID	Spoken	Condition	Expected
sleep_01-07	“dismissed” / “that’s all” / “that’s all, Daimon” / “Daimon, go to sleep” / “Daimon, sleep” / “go to sleep” / “thanks, Daimon, that’s all for now”	Q	Sleep
sleep_08-10	sleep_01, 02, 05	N	Sleep
abort_01	“stop” (said while the assistant is speaking)	Q	Cut TTS, stay AWAKE
abort_02	“cancel that”	Q	Abort request, stay AWAKE
abort_03	“never mind”	Q	Abort request, stay AWAKE
abort_04	“Daimon, stop”	Q	Cut TTS, stay AWAKE
sleepneg_01	“that’s all right with me”	Q	Ignore
sleepneg_02	“I dismissed that idea yesterday”	Q	Ignore
sleepneg_03	“stop by the shop on the way home”	Q	Ignore
sleepneg_04	“that’s all I have to say about it”	Q	Ignore

For abort_01 and abort_04, play a TTS reply through the speakers while you record. Record this separately from the quiet clips, because it also tests echo cancellation.

I. Hindi and code-mixed (10 items, Q & Web AEC)

Goal: Benchmark Hindi / Hinglish phonetics against the name addressing gate.
Distribution: 6 addressed (3 prefix, 3 tail) + 4 unaddressed (negative controls while AWAKE).

ID	Spoken	Structure	Condition	Expected Action
hi_01	“Daimon, aaj ka mausam kaisa hai”	Prefix Addressed	Q	Route to LLM
hi_02	“Daimon, Rahul ko message bhejo ki main dus minute mein pahunch raha hoon”	Prefix Addressed	Q	Route to LLM
hi_03	“Daimon, ek cup chai banane ka timer laga do”	Prefix Addressed	Q	Route to LLM
hi_04	“kal barish hogi kya, Daimon”	Tail Addressed	Q	Route to LLM
hi_05	“Delhi ka temperature kitna hai, Daimon”	Tail Addressed	Q	Route to LLM
hi_06	“meeting kab schedule hui hai, Daimon”	Tail Addressed	Q	Route to LLM
hi_07	“mujhe aath baje jagana”	Unaddressed	Q	Silent drop
hi_08	“kya tum Hindi samajhte ho”	Unaddressed	Q	Silent drop
hi_09	“aaj traffic kaisa hai”	Unaddressed	Q	Silent drop
hi_10	“gaane play karo”	Unaddressed	Q	Silent drop

Web Client AEC Recording Takes (Optional / Pending):
In addition to the 254 direct mic/headset master recordings, optional dedicated takes of this section through the real web client UI (http://localhost:3000) are planned once automated in-browser capture (`NEXT_PUBLIC_RECORD_CORPUS=1`) is implemented:
- **These takes are OPTIONAL and NOT part of the 254 bake-off clips; skip them for initial corpus recording.**
- Browser microphone settings must have Echo Cancellation (AEC) and Noise Suppression active (echoCancellation: true, noiseSuppression: true).
- Validates the browser audio pipeline, WebRTC jitter buffer, and acoustic echo cancellation settling on regional accents and code-mixed phrasing.

Capturing Web AEC takes (RECORD_CORPUS mode — deferred):
Automated in-browser WAV capture via MediaRecorder (`NEXT_PUBLIC_RECORD_CORPUS=1` mode) is deferred. Until it is implemented:
- **Audacity with WASAPI loopback capture on Windows**: records the **raw microphone signal (no browser AEC)**. Label these takes `_audacity_raw_t1` (or `_raw_t1`).
- **Browser-processed AEC takes**: marked as **pending RECORD_CORPUS** mode. When `RECORD_CORPUS=1` is implemented, it will capture the browser AEC-processed `MediaStream` and trigger a WAV download at session end.
- Alternatively, OS-level recording tools set to the communications microphone device can capture the AEC-processed stream. Label true browser AEC takes with `_webaec_t1`.

Scoring rule: Addressed items (hi_01–hi_06) pass if the name gate routes to the LLM. Unaddressed items (hi_07–hi_10) pass if silently dropped. Transcription accuracy (WER) is reported for diagnostic tracking but does not cause pass/fail rejection.

**Item and clip totals:**
- **Phase 1 Bake-off corpus (sections A, C, E, G, I):** 30 + 35 + 40 + 12 + 10 = **127 items / 254 clips** (locked in `evals/corpus/manifest.json`).
- **Full s01 catalog (all sections A–I):** 30 + 13 + 35 + 10 + 40 + 10 + 12 + 18 + 10 = **178 items / 356 clips** (sections B, D, F, H are Phase 1b wake-word corpus).

5. Continuous negative audio (the part that measures false accepts)

Short clips can’t tell you how often the system wakes by mistake. This set can.

Format: unsegmented 16 kHz mono recordings, 10-60 minutes each. No per-clip transcripts, but log every event where “awaken” or the name (or an alias) is actually spoken.
Categories:
TV and streaming in Indian English and Hindi
Family or roommate conversation (several speakers, overlapping)
Phone calls and video meetings
Music with vocals
Podcasts or audiobooks (these will contain “awaken” naturally)
Fan, kitchen or street noise, plus your own typing and coughing
Amount: this is a statistics question, not a preference. With zero false accepts observed, the “rule of three” says the true rate is below roughly 3 divided by hours recorded (at about 95% confidence). Showing under 0.1 per hour therefore needs about 30 hours with none. If you can only record 10 hours, the best claim is “below about 0.3 per hour”. Start with whatever you can get, and say so honestly in the results.
Realistic positives: mix isolated “Awaken.” clips into this audio at several loudness levels. Label these synthetic mixes so they aren’t confused with real recordings.
Rights: use this for private testing only. Don’t redistribute commercial TV or music audio.
6. Ground truth schema (evals/corpus/ground_truth.json)
json
{
  "s01_Q_wake_01_t1.wav": {
    "text": "Awaken",
    "type": "session_wake",
    "speaker_id": "s01",
    "accent_note": "indian_english",
    "environment": "Q",
    "distance_m": 0.1,
    "device": "headset_xyz",
    "split": "dev",
    "expected_action": "open_session",
    "policy_status": "settled",
    "quality_flag": "ok"
  },
  "s01_Q_edge_08_t1.wav": {
    "text": "Hey Daimon, what's the date",
    "type": "name_edge",
    "speaker_id": "s01",
    "environment": "Q",
    "split": "test",
    "expected_action": "TBD",
    "policy_status": "open",
    "quality_flag": "ok"
  },
  "name_01_stt.json": {
    "note": "Log raw STT output for each name_* clip here to build the alias map"
  }
}

Allowed expected_action values: open_session, ignore, route_to_llm, silent_drop, close_session, abort_request, cut_tts, attention_call, TBD. Clips marked policy_status: open are reported separately and never count toward pass/fail.

7. Metrics to report
Metric	Computed from	Starting target (you set the final number before testing)
Wake true-positive rate	Section A (settled items only), per environment and per speaker	Set by you
Wake false accepts per hour	Section 5 continuous audio plus Section B	Under 0.1 per hour (see the statistics note)
Name-gate pass rate	Sections C, E, I	Set by you
Name-gate false accepts	Sections D, F, G	Report counts; Damon/Dayman/demon cases listed separately
Sleep/abort accuracy	Section H, including near-misses	Set by you
Wake-to-chime latency	Measured on the device	Under 500 ms (your earlier target)
Alias map	Section E raw STT logs	n/a (output is the map)

Always report results per speaker, per environment and dev versus test, not just as one overall number.

8. Recording procedure and quality checks
Record in one environment at a time and keep the setup fixed during a block.
Read each line as written, once naturally. Don’t rehearse it into an unnaturally clean delivery.
Don’t re-record clips because the detector failed on them. Re-record only for technical faults (clipping, noise burst, wrong line), and note this in `quality_flags.json`.
After each session, spot-check 10% of clips by listening, and confirm the transcript text matches what was actually said.
Verify and derive using `check_corpus.py` (see [`COMMANDS.md`](COMMANDS.md)).
Don’t tune the detector on the test split.

### Interactive Recorder CLI (`record_session.py`)
To record masters with automatic level checking, live ASCII meter, and resumable session tracking:
```powershell
# 1. List audio input devices to find your mic ID:
uv run --project services/agent python evals/corpus/tools/record_session.py --list-devices

# 2. Record Block Q (Quiet room):
uv run --project services/agent python evals/corpus/tools/record_session.py --env Q

# 3. Record specific sections (e.g., Commands & Name pronunciations):
uv run --project services/agent python evals/corpus/tools/record_session.py --env Q --sections C E
```
**Controls & Workflow:**
- Shows target prompt, delivery note, and filename.
- Press `Enter` to begin recording $\to$ Speak naturally with $\approx 1\text{ s}$ room tone before and after $\to$ Press `Enter` to finish.
- Real-time ASCII volume bar warns if signal is clipping ($\ge -0.05\text{ dBFS}$) or outside nominal bounds ($-18$ to $-3\text{ dBFS}$).
- Clipping errors trigger an immediate retake prompt.
- After take: press `Enter` to accept, `r` to redo, `p` to listen back, `s` to skip, or `q` to quit (all completed takes are saved safely).
- Master WAVs are written directly to `evals/corpus/masters/{speaker}_{env}_{id}_t{take}.wav` (48 kHz mono 24-bit PCM).

### Verification and Derivation Workflow
After recording each block, run:
```powershell
# Check missing clips count
uv run --project services/agent python evals/corpus/tools/check_corpus.py status

# Validate master WAVs for clipping, levels, and room tone (48 kHz mono 24/16-bit)
uv run --project services/agent python evals/corpus/tools/check_corpus.py validate --dir evals/corpus/masters --mode master
# (Convenience shortcut: uv run --project services/agent python evals/corpus/tools/check_corpus.py validate --masters)

# Derive 16 kHz 16-bit mono pipeline WAVs (polyphase resampler)
uv run --project services/agent python evals/corpus/tools/check_corpus.py derive

# Validate derived pipeline WAVs (16 kHz mono 16-bit)
uv run --project services/agent python evals/corpus/tools/check_corpus.py validate
```

9. Changelog and Design Evolution
- Refined sleep/abort semantics and added near-miss negative controls.
- Added speaker spread (s02-s05) and seeded dev/test split locked by item.
- Added continuous negative audio specification with confidence statistical rationale.
- Added name edge cases, name capture set (for STT alias mapping), and phonetic confusable controls.
- Expanded “Awaken” variant set and boundary tests; marked open policies as informational.
- Added environment (Q/D/N), distance, speaker, and accent fields to metadata schema.
- Explicitly defined Hindi / Hinglish scoring (addressed vs unaddressed controls).