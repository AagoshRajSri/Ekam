# Daimon — Real-Time Voice-First Personal AI (Codename: Ekam / Baby)

> **"You speak, interrupt, correct yourself, and change topics; it answers, computes, retrieves, and performs real actions — and tells the truth about what actually happened."**

Daimon is a voice-native personal AI designed from the ground up for sub-second, interruptible conversational interaction. It operates as a low-latency layer between the user and their computing environment, strictly adhering to the priority order: **User Safety & Consent → Truthfulness about Facts and Actions → Latency → Cost → Feature Breadth**.

> ⚙️ **Dynamic Configuration & Zero Hardcoding:** The product name defaults to `os.getenv("APP_NAME", "Assistant")` (configured as **Daimon**, pronounced DAY-mon /ˈdeɪmɒn/), the wake word to `os.getenv("WAKE_WORD", "Awaken")`, and the phonetic respelling to `TTS_NAME_RESPELL=DAY-mon`. All prompts, phonetic normalization logic, and session telemetries derive these values at runtime with zero hardcoded strings. Monorepo packages are scoped under `@daimon/*` and `daimon-agent`.

---

## 📊 Empirical Benchmarks & Verification (No Fake Claims)

All performance figures below are derived from real execution telemetry and empirical test runs. In adherence to the **Truth Over Fluency** principle, mock tests and unverified lab figures are explicitly labeled.

---

### Phase 0: Foundations & Live Console Telemetry

* **LiveKit Cloud Region:** `ap-south` (India South / Mumbai — physical edge node `NM_OHYDERABAD1A`)
* **Transport:** WebRTC (UDP)
* **Date:** 2026-11-07
* **Detailed Report:** [docs/benchmarks/phase_0_empirical_results.md](docs/benchmarks/phase_0_empirical_results.md)

| Pipeline Stage | Provider / Component | Measured Latency | Spec Target | Status |
|---|---|---|---|---|
| **VAD (Voice Activity Detection)** | Silero VAD (Local ONNX, CPU) | **< 1 ms** (in-process) | Local | 🟢 Operational |
| **STT Transcript Delay** | Groq Whisper Large v3 Turbo | **0.78 s – 2.57 s** (median ~1.50 s) | Streaming | 🟢 100% Word Accuracy |
| **End-of-Turn Endpointing** | LiveKit Turn Detector v1 | **400 ms** (fixed commit) | ≤ 700 ms | 🟢 Zero cutoffs |
| **LLM TTFT (Time-to-First-Token)** | Groq `qwen/qwen3.8-27b` | **129 ms – 190 ms** (median ~152 ms) | ≤ 350 ms | ⚡ **>2x Faster than Budget** |
| **TTS TTFB (Time-to-First-Byte)** | Groq Orpheus (`autumn`) | **194 ms – 338 ms** (median ~233 ms) | ≤ 300 ms | 🟢 Crisp Audio Output |
| **Truthfulness Enforcement** | Appendix A Spec Prompt | **100% Pass** | Strict | 🟢 Refused hallucinating time / complex math without tools |

---

### Phase 1: Voice Core, STT Bake-off & Web Telemetry

* **Corpus Evaluated:** 152 dev audio clips (Speaker s01: Quiet [Q], Desk [D], Noise [N] environments)
* **Date:** 2026-11-11
* **Detailed Reports:** [docs/benchmarks/phase_1_bakeoff.md](docs/benchmarks/phase_1_bakeoff.md) & [docs/STATUS.md](docs/STATUS.md)

#### 1. Empirical STT Bake-off (Prompted vs. Unprompted)
We evaluated Groq Whisper Large v3 Turbo across 152 single-speaker baseline audio clips to test whether domain prompt injection improved wake/name recognition:

| Candidate ID | Model | Overall WER | WER (Quiet) | WER (Desk) | WER (Noise) | Entity Accuracy | Name Capture (`Daimon.`) |
|---|---|---|---|---|---|---|---|
| **`groq_whisper` (Unprompted)** | `whisper-large-v3-turbo` | **0.0%** | **0.0%** | **0.0%** | **0.0%** | **100.0%** | **48 / 48 (100%)** |
| `groq_whisper_prompted` | `whisper-large-v3-turbo` | 77.3% | 68.0% | 85.7% | 93.7% | 73.5% | 15 / 48 (Hallucinated/Echoed) |

> ⚠️ **Bake-off Finding (Prompt Leakage):** Under desk (D) and noise (N) acoustic conditions, Whisper's autoregressive decoder echoed words from the injected domain prompt directly into the output transcription. The unprompted configuration achieved **0.0% WER** and captured the assistant name with 100% precision. The domain prompt was permanently removed from the baseline pipeline.

#### 2. Latency Composition & Endpointing Share
Analyzing live WebRTC turn traces ([`telemetry_traces.jsonl`](services/agent/telemetry_traces.jsonl)) revealed the true bottleneck of user-perceived conversational latency:
* **Endpointing Delay Share:** At the 400 ms endpointing delay (`min_delay: 0.4s`), endpointing accounts for **68.3%** of total user-perceived time-to-first-audio (586 ms round trip). At 800 ms (`min_delay: 0.8s`), endpointing accounts for **~81%** of total latency.
* **Per-Turn Telemetry:** Every turn now calculates and broadcasts `stt_requests`, `llm_requests`, `tts_requests`, and rolling `tts_requests_hourly` over the `telemetry` WebRTC data channel.

#### 3. Quota Protection & Failover Chain
* **Guarded Orpheus TTS:** Rolling 100 req/hour limit with disk-persisted timestamps (`tts_quota_timestamps.jsonl`). Proactively transitions to local Piper TTS (`en_US-lessac-medium`) when headroom drops to $\le 10\%$.
* **Local 429 Spoken Recovery:** Pre-rendered local audio (`assets/recovery_429.wav`, 24 kHz mono 16-bit): *"I've hit my voice limit, switching to my backup voice."* (Zero API calls).
* **Idle Auto-Disconnect Watchdog:** Closes both the LiveKit room and agent session after `IDLE_DISCONNECT_SECONDS` (default: 300s) of inactivity.

#### 4. Open Phase 1 Verification Items (Audit Status)
* **Acoustic Barge-in:** In-memory software task cancellation latency was measured at `< 1 ms` (mock test), but physical human-voice-to-silent-speaker acoustic barge-in latency remains **UNVERIFIED** until the 10-trial Audacity test protocol ([docs/live_test_protocol.md](docs/live_test_protocol.md)) is executed with headphones (target: $\le 250\text{ ms}$, ceiling: $\le 300\text{ ms}$).
* **Cloud & Local LLM Failovers:** Secondary cloud failover (`gemini-3.8-flash`) and offline failover (`qwen2.5:7b` via local Ollama) are verified via unit mock tests; live failover API calls are marked **UNVERIFIED LIVE** in CI to prevent flakiness and unintended spend.
* **Continuous Stability:** 30-minute uninterrupted session stability test is pending live browser execution.

---

### Phase 2: Router & Deterministic Tools (Upcoming)

* **Status:** ⏳ **Pending Implementation — No Fabricated Numbers**
* **Scope:**
  * Sub-500 ms Tier-0 regex and grammar evaluator for deterministic queries: arithmetic (`simpleeval` / `sympy`), unit conversions, and datetime.
  * Direct tool execution for real-time weather via Open-Meteo API (zero credentials required).
  * Strict truthfulness verification: tool results must be verified before the model claims an action succeeded.
* **Target Budget:** $\le 500\text{ ms}$ round-trip for deterministic tools; zero LLM calls on pure math/unit questions.

---

## 🏛️ System Architecture

```text
 Client (Web Next.js / Android Companion)
        │
        │ WebRTC (UDP audio + data channel)
        ▼
 LiveKit Cloud (ap-south / Mumbai — node NM_OHYDERABAD1A)
        │
        ▼
 VOICE AGENT (Python 3.12 / livekit-agents 1.8.11)
  ├── VAD & EOT: Silero VAD (local ONNX, <1 ms) + Multilingual Turn Detector
  ├── STT: Groq Whisper Large v3 Turbo (unprompted, 0.0% WER)
  ├── LLM Failover Chain (5.0s timeout):
  │     ├── Tier 1 (Primary): Groq Qwen 3.8 27B (TTFT ~130–180 ms)
  │     ├── Tier 2 (Cloud Failover): Google Gemini Flash
  │     └── Tier 3 (Offline Failover): Local Ollama Qwen 2.5 7B
  └── Guarded TTS (100 req/hr ceiling):
        ├── Primary: Groq Orpheus (autumn)
        ├── Quota / 429 Recovery: Local Piper WAV ("switching to my backup voice")
        └── Fallback: Local Piper TTS (en_US-lessac-medium)
        │
        │ HTTP/2 persistent (Phase 3)
        ▼
 GATEWAY (Node.js / Fastify / TypeScript — Phase 3)
  ├── Auth, Permissions & Audit Logging
  ├── Tool Registry & Verification Engine
  └── BullMQ Background Workers (Redis + PostgreSQL pgvector)
```

---

## 📁 Repository Structure

```text
Ekam/
├── apps/
│   ├── web/                    # Next.js 16.4.5 client, reactive visual orb & telemetry bar
│   └── gateway/                # Fastify Node API, tool registry & workers (Phase 3)
├── services/
│   └── agent/                  # Python voice agent service (livekit-agents 1.8.11)
│       ├── assets/             # Pre-recorded recovery audio (recovery_429.wav)
│       ├── models/piper/       # Local Piper ONNX voice models & JSON configs
│       ├── tests/              # 19 passing unit tests (smoke, telemetry, idle, quota)
│       ├── agent.py            # LiveKit entrypoint, GuardedOrpheusTTS, and watchdog
│       └── pyproject.toml      # Pinned dependencies (uv managed)
├── packages/
│   ├── tool-schemas/           # Zod schemas -> JSON Schema single source of truth
│   └── shared-types/           # Shared TypeScript interfaces across web & gateway
├── evals/
│   ├── bakeoff/                # Multi-provider STT/LLM/TTS bake-off harness & cache
│   └── corpus/                 # Audio benchmark corpus, manifests, and split.lock
├── docs/
│   ├── adr/                    # Architecture Decision Records (001 through 004)
│   ├── benchmarks/             # Empirical benchmark logs (Phase 0, Phase 1 bake-off)
│   ├── STATUS.md               # Source of truth project status and open exit criteria
│   └── live_test_protocol.md   # Audacity barge-in and live testing instructions
├── .env.example                # Clean environment template (zero secrets)
├── pnpm-workspace.yaml         # pnpm monorepo workspace configuration
└── README.md                   # Project overview, empirical benchmarks, and guides
```

---

## 🚦 Roadmap & Phase Progress

- [x] **Phase 0 — Foundations:** Monorepo scaffolding, credentials verification, ADRs, Python agent implementation, and live console WebRTC verification ([`phase_0_empirical_results.md`](docs/benchmarks/phase_0_empirical_results.md)).
- [x] **Phase 1 — Voice Core & Web Client (Development Prototype):** Next.js client (`apps/web`), reactive visualizer orb, telemetry data channel, Guarded Orpheus TTS (100 req/hr), Silero VAD, STT bake-off, and idle auto-disconnect.
  - *Exit criteria remaining:* Live Audacity acoustic barge-in measurement ($\le 250\text{ ms}$) and 30-min continuous stability test.
- [ ] **Phase 1b — Wake Word & Session Gate (Proposed):** On-device WASM pre-gating keyword engine, "Awaken" acoustic model evaluation, and Section E name alias gating (see [`docs/adr/004-wake-word-and-session-architecture.md`](docs/adr/004-wake-word-and-session-architecture.md)).
- [ ] **Phase 2 — Router & Deterministic Tools:** Sub-500 ms Tier-0 regex/grammar evaluator (arithmetic, units, time conversions) and Open-Meteo weather integration.
- [ ] **Phase 3 — Gateway, Data & Memory:** Fastify gateway, PostgreSQL + pgvector long-term memory, Redis session state, and write-behind workers.
- [ ] **Phase 4 — Tool Ecosystem & Permissions:** Verified tool contracts, human-in-the-loop confirmation policies, and prompt-injection taint tracking.
- [ ] **Phase 5 — Android Companion:** Jetpack Compose companion app, deep-link handoffs, and honest action reporting.
- [ ] **Phase 6 — Background Research & Proactive RAG:** BullMQ research pipelines, cited summaries, and quiet-hours proactive notifications.
- [ ] **Phase 7 — Optimization & Local AI:** Tail latency tuning, semantic caching, and on-device SLM execution.
- [ ] **Phase 8 — Hardening & Launch:** Security review, failover drills, privacy compliance (DPDP), and multi-user isolation.

---

## ⚡ Quickstart

### Prerequisites
* Node.js LTS (>= 20) & `pnpm` (>= 10)
* Python 3.12 & `uv` package manager
* LiveKit Cloud account & Groq API key

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/AagoshRajSri/Ekam.git
cd Ekam

# Set up environment variables
cp .env.example .env
# Configure LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and GROQ_API_KEY in .env

# Install monorepo web & gateway dependencies
pnpm install

# Set up Python agent virtualenv
cd services/agent
uv sync
```

### 2. Run Test Suites
```bash
# Run unit & smoke tests (all offline / zero quota used)
uv run pytest tests/test_agent_smoke.py tests/test_telemetry_and_idle.py -v

# Verify web client build
pnpm --filter @daimon/web build
```

### 3. Launch Live Development Stack
Open two terminal windows:

```bash
# Terminal 1: Web Client (Next.js)
pnpm --filter @daimon/web dev

# Terminal 2: Voice Agent (LiveKit worker)
cd services/agent
uv run python agent.py dev
```

Navigate to `http://localhost:3000` to interact with Daimon, observe the real-time latency waterfall, and monitor per-turn telemetry counters.

---

## 📄 License
ISC © 2026 Ekam / Daimon Contributors
