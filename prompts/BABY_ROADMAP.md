# BABY — Step-by-Step Roadmap

> Companion to `BABY_PROMPT_v2.md`. That document says **what** Baby must be; this one says **in what order, where, and how** to build it, what it looks like when finished, and how to know each step is done.
>
> **Timeline assumption:** one developer, ~15–20 focused hours/week. Durations are rough ranges, not promises. Total ≈ **5–7 months** to a hardened, daily-usable Baby; a **talking, interruptible, fast MVP exists after ~3–4 weeks**.

> **Naming:** the project is codenamed *Baby* in these files, but the product name and wake word are config values (`APP_NAME`, `WAKE_WORD`; currently **Ekam**). Never hard-code either; do not rename files or code.

---

## Part 1 — What it looks like in the end

### 1.1 The experience
You say "Baby, what's the weather?" and audio starts before you've finished registering you're done talking. You interrupt mid-sentence and it stops instantly. You say "text Rahul I'm reaching in ten minutes"; it reads back *who* and *what*, you say "yes", and it tells you the truth about what happened ("Sent" only when confirmed; "I've opened WhatsApp with the message ready" when you still have to tap). Math, time, and timers answer near-instantly without an LLM. Long research runs in the background and pings you when done. You can ask "what do you remember about me?" and delete anything.

### 1.2 Main screen (web + Android share the same layout language)
```text
┌────────────────────────────────────────────────────────────────────────┐
│ BABY        ● Connected · Mumbai · 38 ms              ⚙ Settings  🧠 Memory │
├──────────────────────────────────┬─────────────────────────────────────┤
│                                  │  TRANSCRIPT                         │
│           ╭──────────╮           │  You   what's the weather?          │
│        ╭──┤   orb    ├──╮        │  Baby  Right now it's 29 degrees,   │
│        │  │ reacts   │  │        │        partly cloudy.               │
│        ╰──┤ to audio ├──╯        │  You   and tomorrow?                │
│           ╰──────────╯           │  Baby  Tomorrow, 31 with a chance…  │
│                                  ├─────────────────────────────────────┤
│         S P E A K I N G          │  ACTIVE TASKS                       │
│      ▁▂▃▅▇▅▃▂▁  waveform         │  ⏱ Timer            06:42 left      │
│                                  │  🔎 Research: laptops < ₹80k  72%  │
│   tool: weather ✓ 212 ms         │  ⏰ Umbrella reminder · 8:00 AM     │
├──────────────────────────────────┴─────────────────────────────────────┤
│ CONFIRM  WhatsApp → Rahul Sharma (…4821)                               │
│ "I'm reaching in 10 minutes"            [ Open WhatsApp ] [ Edit ] [ ✕ ] │
├────────────────────────────────────────────────────────────────────────┤
│ dev ▸ EOT 310 · LLM 240 · TTS 95 · first-audio 780 ms · tier 1 · $0.0009 │
└────────────────────────────────────────────────────────────────────────┘
```

| State | Orb behaviour |
|---|---|
| IDLE | Slow breathing, dim |
| LISTENING | Reacts to your mic level |
| THINKING | Subtle rotation |
| EXECUTING | Ring + tool chip ("calendar…") |
| SPEAKING | Pulses with Baby's audio |
| CONFIRMING | Amber ring + confirmation card |
| ERROR/DEGRADED | Red edge + one-line reason |

**Other screens:** Memory manager (view/edit/delete) · Connections & permissions (per-tool risk policy, OAuth accounts) · Task history · **Dev telemetry dashboard** (latency waterfall per turn, p50/p95 per stage, cost, failover events).

### 1.3 Final system
```text
 ┌── Clients ────────────────────┐
 │ Web (Next.js)                 │
 │ Android companion (Kotlin)    │──── WebRTC ────┐
 │ Desktop helper (Tauri, later) │                │
 └───────────────▲───────────────┘                ▼
                 │ WebSocket events        ┌──────────────┐
                 │ + device commands       │ LiveKit Cloud │  (Mumbai / ap-south)
                 │                         └──────┬───────┘
                 │                                ▼
                 │                  ┌──────────────────────────────┐
                 │                  │ VOICE AGENT (Python)          │  same region as models
                 │                  │ VAD → EOT → STT               │
                 │                  │ Tier 0 rules                  │──► STT / LLM / TTS providers
                 │                  │ Tier 1 fast LLM + tools       │    (failover chains)
                 │                  │ Tier 2 escalation             │
                 │                  │ Streaming TTS                 │
                 │                  └───────────────┬──────────────┘
                 │                                  │ HTTP/2, persistent
                 │                                  ▼
                 │                  ┌──────────────────────────────┐
                 └──────────────────│ GATEWAY (Node/Fastify)        │──► Google/Microsoft/Spotify/Maps…
                                    │ auth · registry · permissions │
                                    │ verify · audit · events       │
                                    └───────┬──────────────┬───────┘
                                            │              │
                                  ┌─────────▼───┐   ┌──────▼─────────┐
                                  │ Redis       │   │ PostgreSQL     │
                                  │ session     │   │ + pgvector     │
                                  │ pub/sub     │   │ users·memory   │
                                  │ BullMQ      │   │ audit·tasks    │
                                  └─────┬───────┘   └────────────────┘
                                        ▼
                              BullMQ workers: research · reminders · memory write-behind
```

### 1.4 Deployment topology (target)
| Component | Where | Notes |
|---|---|---|
| LiveKit | LiveKit Cloud | Real-time transport; self-host only if cost/compliance forces it |
| Voice agent | LiveKit Cloud agent hosting in **ap-south (Mumbai)** — or a container on a small VM in Mumbai | Agent region can't be changed after creation; choose deliberately. Keep it next to your model endpoints |
| Gateway + workers | Container(s) in the same region (Fly.io / Render / a VPS / cloud VM) | One small instance is enough for a long time |
| PostgreSQL | Managed, same region | pgvector enabled |
| Redis | Managed, fixed-price, no-eviction policy | Required for BullMQ |
| Web client | Vercel or same host as gateway | Token minting lives on the gateway |
| Observability | OpenTelemetry → Grafana (or Langfuse for LLM traces) | Latency dashboard is a product feature, not an afterthought |

### 1.5 Repo layout (monorepo)
```text
baby/
├─ apps/
│  ├─ web/                 # Next.js client + dev telemetry UI
│  ├─ gateway/             # Fastify API, tool registry, permissions, workers
│  ├─ android/             # Kotlin companion (Phase 5)
│  └─ desktop/             # Tauri helper (optional, later)
├─ services/
│  └─ agent/               # Python LiveKit voice agent
│     ├─ router/           # Tier-0 rules, model policy
│     ├─ tools_local/      # hot-path-safe tools
│     ├─ prompts/          # system_v1.md …
│     └─ metrics/
├─ packages/
│  ├─ tool-schemas/        # Zod → JSON Schema (single source of truth)
│  └─ shared-types/
├─ evals/
│  ├─ corpus/              # recorded WAVs + ground truth JSON
│  ├─ latency_replay/
│  ├─ golden_conversations/
│  └─ safety/
├─ infra/                  # docker-compose, deploy configs
└─ docs/adr/               # decision records
```

---

## Part 2 — Tech stack (with the reason for each choice)

| Layer | Choice | Why |
|---|---|---|
| Transport | **LiveKit (WebRTC/UDP)** | Solves audio transport, reconnection, echo handling, and gives an agent framework with turn-taking built in |
| Agent framework | **`livekit-agents` (Python)** | Current versions ship turn-detection models, adaptive interruption handling, and preemptive generation as configuration rather than code you write |
| VAD | **Silero** (loaded once per process) | Local, fast, no network hop |
| End-of-turn | LiveKit turn-detector model **or** Deepgram Flux's built-in turn detection | Flux exposes early "eager" end-of-turn events that let the LLM start before the turn is confirmed (cost: noticeably more LLM calls on speculative starts) |
| STT | **Deepgram** (Nova-3 / Flux) baseline; **Sarvam** if you go Indic or code-mixed | LiveKit Inference hosts Deepgram in Mumbai; Sarvam has a first-party LiveKit plugin with broad Indian-language coverage. Decide by your benchmark |
| TTS | **Cartesia Sonic** or **ElevenLabs Flash**; Sarvam for Indic voices | Vendors claim roughly 40–150 ms time-to-first-audio — treat as marketing until you measure it from Mumbai |
| Fast LLM | **Groq**-hosted model, or a **Gemini Flash-tier** model with thinking at minimum, or **Claude Haiku 5.5** | TTFT varies enormously by provider, region, and thinking level — pick by measurement |
| Reasoning LLM | **Claude Sonnet 5.5 / Opus 5.5** (or Gemini Pro-tier) | Only for Tier 2 with a spoken hand-off |
| Gateway | **Node.js + TypeScript + Fastify + Zod** | Fast, typed, great integration ecosystem (OAuth, Google APIs, Stripe later) |
| ORM / DB | **Prisma + PostgreSQL + pgvector** | One durable store for relational data *and* vectors |
| Cache / queue | **Redis + BullMQ** | Session state, pub/sub, delayed jobs (reminders), background research |
| Embeddings | **FastEmbed (ONNX, local)** | No network hop, small footprint |
| Math / units | **`simpleeval`/`sympy` (safe eval), `pint`, `zoneinfo`** | Deterministic; never `eval()` |
| Weather (dev) | **Open-Meteo** | No API key, simple; swap for a paid provider if you need SLA |
| Sandbox | Container/gVisor/Firecracker or a managed sandbox | For code/browser/filesystem tools |

**Cost model (measure, don't guess):** cost per minute ≈ STT + LLM (in+out tokens) + TTS characters + LiveKit agent-session minutes (billed at roughly $0.01/min after included quota — check current pricing). Emit `cost_usd` on every turn trace from Phase 1 so the dashboard tells you the real number. Preemptive generation and eager end-of-turn trade extra LLM calls for lower latency — track the cost of that trade.

---

## Part 3 — Timeline at a glance

| Phase | Name | Duration | Milestone you can demo |
|---|---|---|---|
| 0 | Foundations | 3–5 days | Talk to Baby in your terminal |
| 1 | Voice core | 2–3 wks | Fast, interruptible voice chat in the browser, deployed in Mumbai |
| 2 | Router + deterministic tools | ~2 wks | Instant math/time/timers; weather with follow-ups |
| 3 | Gateway, data, memory | 2–3 wks | "Remember I prefer Celsius" survives restarts |
| 4 | Tool ecosystem + permissions | 3–4 wks | Calendar/email/reminders with confirmations and verification |
| 5 | Device integration (Android first) | 4–6 wks | "Call Mom", timers, WhatsApp handoff from your phone |
| 6 | Background research & proactive | 2–3 wks | "Research laptops under ₹80,000" → notification |
| 7 | Optimization & local AI | ongoing | Only what benchmarks justify |
| 8 | Hardening & launch | ~2 wks | Security review, load test, runbooks |

**Rule:** do not start a phase until the previous phase's exit criteria are met and measured.

---

## Profile A overrides (read before Part 4)

This roadmap describes the **target** build. While in **Profile A (free)** (see `BABY_FREE_TO_PREMIUM.md`), apply these overrides:

- **Accounts (Phase 0):** create only free-tier accounts: LiveKit Build, Groq, Google AI Studio. Skip Deepgram, paid TTS, and Anthropic until Profile B is unlocked. Docker/Postgres/Redis are not needed until Phase 3.
- **Phase 1 code skeleton:** it names paid providers. Treat it as structure only; wire the free providers (local faster-whisper or LiveKit Inference credits for STT, Piper/Kokoro for TTS, Groq then Gemini then Ollama for the LLM).
- **Deployment:** run the agent locally. The Mumbai/managed-hosting steps (Phase 1 step 6, Day 6) and managed Postgres/Redis are Profile B.
- **Latency targets:** under Profile A these are *baselines to record*, not blockers. Functional, safety, and honesty criteria stay blocking; barge-in must work.
- **Preemptive generation:** off.
- **Language:** record the corpus in Indian English, plus ~10-20 extra unscored Hindi/code-mixed utterances and ~20 repetitions of the wake word in quiet, noisy, and speakerphone conditions.

---

## Part 4 — Phase-by-phase build plan

### Phase 0 — Foundations (3–5 days)

**Goal:** remove decision friction and create the measuring stick *before* writing product code.

**Where:** repo root, `evals/corpus/`, `docs/adr/`.

**Steps**
1. Create the monorepo (`pnpm` workspaces for TS, `uv` for Python). Add lint, format, and a pre-commit hook. Skip Docker/Postgres/Redis for now — you don't need them yet.
2. Create accounts and keys: LiveKit Cloud, Deepgram, one TTS vendor, Groq, Google AI Studio, Anthropic. Put them in `.env` (git-ignored) plus `.env.example`.
3. **Record the benchmark corpus:** 50–100 WAV files (16 kHz mono) of *you* speaking: commands, questions, contact names, numbers, currency, corrections, plus some in a noisy room and on speakerphone. Save ground-truth transcripts in JSON. This is the most valuable asset in the project.
4. Write **ADR-001** (initial stack) and **ADR-002** (latency definitions: what exactly `T_speech_end` and `T_first_audio` mean).
5. Install the LiveKit CLI; run the official voice-agent quickstart end-to-end.

**Exit:** you can speak to an agent in a terminal console and hear it reply; corpus and ADRs exist.

---

### Phase 1 — Voice core (2–3 weeks)

**Goal:** natural, fast, interruptible conversation. Nothing else.

**Where:** `services/agent/` (Python) + `apps/web/` (minimal Next.js).

**Steps**
1. **Console agent.** Wire Silero VAD → STT → LLM → TTS with `AgentSession`. Skeleton (verify names/signatures against docs for your installed version — the API moves quickly):
```python
# services/agent/agent.py
from livekit import agents
from livekit.agents import Agent, AgentSession, TurnHandlingOptions, JobContext, WorkerOptions, cli
from livekit.plugins import silero, deepgram, cartesia, groq
from livekit.plugins.turn_detector.multilingual import MultilingualModel

SYSTEM_PROMPT = open("prompts/system_v1.md").read()   # Appendix A of the spec

class Baby(Agent):
    def __init__(self):
        super().__init__(instructions=SYSTEM_PROMPT)

def prewarm(proc: agents.JobProcess):
    proc.userdata["vad"] = silero.VAD.load()          # once per process, not per session

async def entrypoint(ctx: JobContext):
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model="nova-3", language="en-IN"),      # or Flux via its plugin — benchmark both
        llm=groq.LLM(model="<fast-model-id>"),
        tts=cartesia.TTS(model="<sonic-model-id>", voice="<voice-id>"),
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
            endpointing={"mode": "fixed", "min_delay": 0.4, "max_delay": 3.0},
            interruption={"mode": "adaptive", "min_duration": 0.4, "resume_false_interruption": True},
            preemptive_generation={"preemptive_tts": False},
        ),
    )
    await session.start(agent=Baby(), room=ctx.room)
    await session.generate_reply(instructions="Greet the user in one short sentence.")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
```
   Run with `python agent.py console`, then `python agent.py dev`.
2. **Web client.** A Next.js route handler mints short-lived LiveKit tokens (`livekit-server-sdk`). The page uses the LiveKit React components: room, audio renderer, and the voice-assistant hook for state + visualizer. Start with a plain orb and a transcript; polish later.
3. **Voice system prompt** (spec Appendix A v2): short answers, no markdown, spoken numbers. Use the fixed default style values and omit the "TUNING THE VOICE" block until Phase 3.
4. **Telemetry from day one.** LiveKit Agents emits per-component metrics (end-of-utterance delay, LLM TTFT, TTS TTFB). Subscribe and write one JSON line per turn with the trace shape in the spec (§14). Add `cost_usd`.
5. **Provider bake-off** on your corpus: STT (Deepgram Nova-3 vs Flux vs Sarvam), TTS (Cartesia vs ElevenLabs Flash vs Deepgram Aura-2 vs Sarvam), LLM (Groq vs Gemini Flash-tier with minimal thinking vs Claude Haiku 5.5). Record results in **ADR-003**. Pick primary **and** fallback for each.
6. **Deploy early** to LiveKit Cloud `ap-south` (Mumbai) and re-measure — numbers from your laptop or a US region will mislead you.
7. **Turn-taking tuning:** adjust endpointing delays, adaptive-interruption thresholds, and false-interruption recovery using real recordings of yourself pausing, correcting, and coughing.
8. **Scripted barge-in test:** play audio at Baby mid-sentence and assert silence within the budget.

**Exit criteria**
- Deployed agent: **p50 speech-end → first audio ≤ 1.0 s** over a 20-turn scripted conversation
- Barge-in: **≤ 300 ms** to silence
- 30-minute session without a crash; recovers after toggling the network
- ADR-003 with benchmark tables and fallbacks

**Watch-outs**
- Eager end-of-turn / preemptive generation multiplies LLM calls (Deepgram cites roughly 50–70 % more). Keep it while the latency win justifies the cost.
- **Never let a speculative pass execute a side-effecting tool** (relevant from Phase 2 on).
- High "thinking" levels on flash-class models can add seconds of TTFT — turn it down for the voice path.
- Test with headphones first; speaker echo will make you chase phantom bugs.

---

### Phase 2 — Router + deterministic tools (~2 weeks)

**Goal:** Baby stops treating everything as generic chat.

**Where:** `services/agent/router/`, `services/agent/tools_local/`.

**Steps**
1. **Define the tool contract** (spec §6.1). Python side: pydantic models mirroring the `ToolResult` union. Keep the shape identical to what the gateway will use in Phase 3.
2. **Tier-0 rules** — start tiny and precise:
```python
import re
CONTROL = re.compile(r"^(?:baby[, ]+)?(stop|cancel that|never ?mind|be quiet|quiet)\W*$", re.I)
ARITH   = re.compile(r"^(?:what(?:'s| is)\s+)?(?P<expr>[\d\s.,+\-*/x×÷()%]+|.*\b(?:plus|minus|times|divided by|percent)\b.*)\??$", re.I)

def tier0(text: str):
    t = text.strip()
    if CONTROL.match(t):
        return ("stop", {}, 1.0)
    # …time/date, timers, unit conversion, percentages…
    return None          # fall through to Tier 1 — NEVER guess
```
   Use a **safe evaluator** (`simpleeval`/`sympy`), `pint` for units, `zoneinfo` for time. Normalize spoken forms ("times", "into", "point five") to an expression first.
3. **Tier-1 tools** via LLM tool calling: `weather` (Open-Meteo), `web_search` (any search API returning clean snippets), `datetime`.
4. **Entity store** in the session: `last_location`, `last_contact`, `last_topic`, so "what about tomorrow?" resolves.
5. **Acknowledgement phrases:** pre-synthesize 5–10 short lines ("One sec.", "Checking that.") and play them when a tool exceeds ~800 ms.
6. **Router decision log** on every turn; this becomes your training set.
7. **Model policy v1** as a config file (which model per tier, timeouts, fallbacks); add the `escalate` tool with a spoken hand-off for Tier 2.
8. **Label 100+ utterances** by expected tier and measure.

**Exit criteria**
- Tier-0 **precision ≥ 99 %** on the labeled set (recall improves over time)
- Math/unit tests 100 % correct; "273 × 491" answers **134,043** with no LLM call in the trace
- Weather + "what about tomorrow?" works
- Tier-0 p50 ≤ 500 ms; fast path still ≤ 1.0 s

---

### Phase 3 — Gateway, data, memory (2–3 weeks)

**Goal:** durable state without hurting latency.

**Where:** `apps/gateway/`, `infra/docker-compose.yml`, agent integration.

**Steps**
1. `docker-compose`: PostgreSQL (with pgvector) + Redis.
2. **Prisma schema:** `users, devices, sessions, memories, permissions, tool_calls, tasks, audit_logs`.
3. **Auth:** single-user first (Google OAuth or passkeys). Token minting for LiveKit moves from the Next.js route to the gateway.
4. **Bootstrap endpoint:** at session start the agent makes **one** call that returns profile, preferences, top-K memories, and the tool manifest. Cache in-process. This is how the hot path stays free of DB queries.
5. **Redis session state:** conversation window, entity store, action stack, pending confirmations — with TTLs. The agent reads its in-process copy and writes to Redis asynchronously.
6. **Long-term memory tools:** `remember`, `recall`, `forget`. Embed with FastEmbed → pgvector. Recall runs in parallel with STT finalization under a 50 ms budget; on timeout, continue without.
6b. **Style preferences (persona tuning):** add `style_preferences` (humor, fillers, formality, verbosity; defaults 1/1/1/1) to the profile and return it in the bootstrap call so it is injected into the system prompt with no hot-path query. Add the `update_style_preferences` tool (risk `LOW`, announced). Switch the agent to Appendix A v2 including the "TUNING THE VOICE" block. The first-session style check fires once; later changes happen only on request or a repeated correction.
7. **Memory manager UI:** list, edit, delete, provenance. Add "what do you remember about me?" by voice.
8. **BullMQ worker** for write-behind: memory saves, conversation summaries, analytics.
9. **Trace propagation:** `traceparent` from agent → gateway → workers.

**Exit criteria**
- Kill and restart the agent mid-session → context restored
- "Remember I prefer Celsius" persists across sessions; "forget that" deletes it (verify in the database)
- Traces prove **zero Postgres queries on the hot path**
- "Fewer ums" / "be more casual" changes style, persists across sessions, and can be read back or reset by voice (golden #9)
- p50 latency regression **≤ 5 %** vs Phase 2

---

### Phase 4 — Tool ecosystem + permissions (3–4 weeks)

**Goal:** real actions, safely, with honest verification.

**Where:** `apps/gateway/src/tools/`, `packages/tool-schemas/`, web confirmation UI.

**Steps**
1. **Tool registry:** Zod schemas → JSON Schema export → agent fetches the manifest. One source of truth.
2. **Permission manager** (the policy function is deliberately small and testable):
```typescript
export function decide(tool: BabyTool<any, any>, ctx: PolicyCtx): Decision {
  if (ctx.killSwitch)                         return deny('kill_switch');
  if (!hasScopes(ctx.grantedScopes, tool))    return askToConnect(tool);
  if (ctx.turnTainted && tool.risk !== 'READ_ONLY')
                                              return confirm('screen');   // untrusted content in this turn
  const policy = ctx.userOverrides[tool.name] ?? DEFAULT_POLICY[tool.risk];
  switch (policy) {
    case 'allow':          return allow();
    case 'announce':       return allowAndAnnounce();
    case 'verbal_confirm': return confirm('voice', readback(tool, ctx.params));
    case 'screen_confirm': return confirm('screen', readback(tool, ctx.params));
  }
}
```
3. **Confirmation state machine** in Redis: single-use, ~30 s expiry, bound to the exact parameters read back.
4. **OAuth connections** (Google first): encrypted refresh tokens (envelope encryption), least-privilege scopes requested incrementally.
5. **Build tools in this order** (each with schema, risk, policy, verification, tests):
   `calendar (read → create)` → `reminders (BullMQ delayed jobs + push)` → `contacts` → `email (read/summarize → draft → send)` → `maps` → `music` → `documents/RAG` → `browser (read-only, sandboxed)`.
6. **Contact resolution:** fuzzy + phonetic matching; feed your contact names to the STT as custom vocabulary/keyterms; **always read back** the resolved contact.
7. **Verification per tool:** event created → read it back by ID; email sent → find the message ID in Sent; reminder → job exists and delivery receipt logged.
8. **Undo/action stack** and the global "stop everything" kill switch.
9. **Injection defenses:** delimiter-wrap all external content; taint flag as in the policy function above; add safety evals.

**Exit criteria**
- Golden conversations #1, #4, #5, #6 pass in automated audio replay
- Every tool: schema + risk level + policy + verification + failure path + tests
- Audit log shows every call; "Baby, stop everything" halts tasks in ≤ 500 ms
- p50 latency unchanged for read-only tools

---

### Phase 5 — Device integration (4–6 weeks)

**Goal:** control the phone honestly, using only supported mechanisms.

**Recommendation:** Android first (more permissive intents and broader reach in India). If you live on iOS, invert the plan around Shortcuts/App Intents and accept tighter limits.

**Where:** `apps/android/`, a device command channel in the gateway.

**Steps**
1. **Companion app** (Kotlin, Jetpack Compose, LiveKit Android SDK): same room/session protocol as web. Use a visible foreground service while the mic is active. Tap-to-talk first; wake word later (Phase 7).
2. **Device command channel:** gateway → device via LiveKit data/RPC or FCM push. Define a `DeviceCommand` schema and a **capability manifest** the device reports (which capabilities exist and which permissions are granted). Results flow back for verification.
3. **Implement in this order:** open app → timer/alarm (`AlarmClock` intents) → call (dial intent, direct call only with explicit permission) → SMS (compose intent, user taps send) → **WhatsApp (`wa.me` deep link with prefilled text, user taps send)** → music control → location → settings panels (Bluetooth/Wi-Fi where toggling isn't allowed).
4. **Honest status mapping:** launching a compose screen returns `handed_off`, not `success`. Baby says "I've opened WhatsApp with the message ready."
5. **Desktop helper (optional):** Tauri app exposing a localhost tool server behind a token; allow-listed operations only (open app, media keys, file search in approved folders). Every capability is off until you enable it.
6. **Permissions UX on device:** request runtime permissions lazily, explain why, and reflect them in the capability manifest.

**Exit criteria**
- "Call Mom", "set a timer for ten minutes", "open Spotify", "text Rahul…", "WhatsApp Rahul…" work with correct readbacks
- Golden #8: Baby **never says "sent"** for user-tap flows
- Airplane-mode / permission-denied paths produce clear spoken recovery

---

### Phase 6 — Background research, proactive help, personal RAG (2–3 weeks)

**Goal:** heavy work never touches the voice loop.

**Steps**
1. **Research job pipeline (BullMQ):** plan → parallel searches → fetch → extract → synthesize with a reasoning model → store artifact → notify. Baby says "Got it, I'll research that" and returns to listening immediately.
2. **Notification path:** push notification + "your research is ready" spoken at the next session start; results shown in the UI with sources.
3. **Personal RAG:** ingest Drive/notes (chunk → FastEmbed → pgvector), retrieve with citations, enforce per-source permissions.
4. **Proactive reminders:** scheduler that considers calendar and context, with **quiet hours, rate limits, and per-category opt-in**. Proactivity that annoys gets turned off — make it stingy.

**Exit criteria**
- A 3-minute research task runs while you keep chatting; voice latency unaffected (compare traces)
- Sources are cited; user can delete stored results

---

### Phase 7 — Optimization & local AI (ongoing, 2–4 weeks bursts)

**Rule:** only ship what a benchmark justifies. Suggested order by expected payoff:

1. Tune end-of-turn thresholds and preemptive generation using your logged turns
2. Confirm every stage is co-located (agent ↔ STT/LLM/TTS)
3. Shorten and prompt-cache the system prompt; trim tool descriptions
4. Expand Tier 0 using the router log ("what do people say that never needed an LLM?")
5. Tiny ONNX intent classifier trained on the router log (only if it beats the rules)
6. Semantic cache for STATIC answers (only if hit-rate data justifies it; watch false hits)
7. Local wake word and on-device VAD
8. Small local LLM for private/offline cases

**Exit:** each retained component has a before/after table (latency, quality, cost, privacy).

---

### Phase 8 — Hardening & launch (~2 weeks)

- **Security review:** injection red-team, confirmation-bypass attempts, token storage audit, dependency scan
- **Load test:** concurrent sessions per agent worker (CPU-bound — size workers from measurements)
- **Reliability:** failover drills (kill each provider), backups and restore test, runbooks
- **Privacy:** retention jobs, export/delete, consent screens; review India's DPDP Act obligations before onboarding other users
- **Ops:** alerts on p95 latency, failover rate, tool failure rate, cost per user
- **Multi-user readiness:** quotas, rate limits, per-user encryption keys (if you go beyond one user)

---

## Part 5 — Risks and mitigations

| Risk | Mitigation |
|---|---|
| Latency creeps as features land | Latency replay in CI; every hot-path PR reports a delta; hot-path rule enforced by tracing |
| Provider outage or slowdown | Failover chains, circuit breakers, degraded modes |
| Platform limits (WhatsApp, iOS, Bluetooth toggles) | Design around official intents/deep links; report `handed_off` honestly |
| Prompt injection via email/web | Untrusted-content rule, taint tracking, forced confirmation, safety evals |
| STT mishears a contact name → wrong recipient | Custom vocabulary + phonetic matching + mandatory readback |
| Cost blow-up from speculative LLM calls | `cost_usd` on every trace; per-session caps; tune thresholds |
| Scope creep / solo-dev burnout | Phase gates; each phase ends in a demo you can actually use |
| Vendor lock-in | Provider interfaces; ADR-backed choices; fallbacks from day one |

---

## Part 6 — Your first 7 days

1. **Day 1:** Create the repo, accounts, and keys; run the LiveKit quickstart in console mode.
2. **Day 2:** Record the 50–100 utterance corpus with ground truth.
3. **Day 3:** Write ADR-001/002; get a console agent running with your chosen defaults.
4. **Day 4:** Add the Next.js token route and a minimal voice page; talk to it from the browser.
5. **Day 5:** Add per-turn telemetry (EOT, TTFT, TTS TTFB, cost) as JSON lines.
6. **Day 6:** Deploy the agent to Mumbai; re-measure.
7. **Day 7:** Try the first bake-off (two STTs × two TTS × two LLMs) on your corpus; write ADR-003 draft.

By the end of week one you should hear Baby answer in your browser with real latency numbers in front of you — everything after that is an ordered, measurable climb.
