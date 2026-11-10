# BABY — Build Profiles: Free First, Premium Later

> Companion to `BABY_PROMPT_v2.md` and `BABY_ROADMAP.md`.
> **Profile A = free build (do this first, completely).** **Profile B = premium build (only after A is finished, and only where measurements justify it).**

---

## 1. Paste-ready policy prompt for AI coding agents

```text
BUILD PROFILE POLICY — READ BEFORE WRITING ANY CODE

Baby is built in two profiles. Finish Profile A (FREE) completely before touching Profile B (PREMIUM).

1. PROFILE A IS THE DEFAULT. Every phase is built with free tiers, local models, and
   open-source software only. Do NOT add paid-provider SDKs, adapters, keys, or config
   during Profile A. Do not "prepare" premium code early.

2. DESIGN FOR SWAPPING FROM DAY ONE. Every external capability (transport, VAD/turn
   detection, STT, LLM, TTS, search, database, cache, hosting) sits behind an interface and a
   config-driven provider registry. A premium switch must be: one new adapter + one config
   change. Never a rewrite, never a change to the router, tools, permissions, or memory logic.

3. PROFILE B IS LOCKED until ALL of these are true:
   a) Profile A meets the exit criteria of Phases 1–4 (and Phase 5/6 if those are in scope).
   b) The user explicitly says "start premium upgrades".
   c) Telemetry shows a specific layer is the measured bottleneck (see Trigger metrics in the
      upgrade table). If a layer is not a measured bottleneck, it stays on Profile A.

4. UPGRADE ONE LAYER AT A TIME, in the order defined in the Upgrade Order. For each layer:
   - Benchmark Profile A vs candidate(s) on the recorded corpus, from the deployment region.
   - Write an ADR with the numbers (p50/p95 latency, error rate, cost per turn).
   - Ship behind a feature flag; keep rollback to Profile A one config change away.
   - Keep the Profile A provider as the LAST entry in the failover chain (free = safety net).
   - Keep the change only if it beats A by the agreed threshold; otherwise revert and log why.

5. COST GUARDRAILS. Before enabling any paid provider: prepaid credits or hard spend limit,
   auto-recharge OFF, per-day spend cap in config, cost_usd on every turn trace, alert at 80 %.

6. NOTHING ELSE CHANGES. Permissions, confirmation policies, verification rules, prompt-injection
   defenses, and honesty rules apply identically in both profiles.

7. VERIFY BEFORE USING. Provider APIs, model names, prices, and free-tier limits change often.
   Check current official docs before writing an adapter; never guess signatures.

8. IF UNSURE whether a premium switch is authorised, assume it is NOT and ask once.
```

---

## 2. Profile A (free) — reference

| Layer | Free choice |
|---|---|
| Transport | LiveKit Cloud **Build** plan, agent run on your own PC (or self-hosted LiveKit) |
| VAD / turn detection | Silero VAD + LiveKit turn-detector (falls back to a local model when free quota ends) |
| STT | Groq Whisper (utterance-based, no partial transcripts; model ID pinned in ADR-003) → local faster-whisper fallback |
| Fast LLM | Groq free tier (model ID pinned in ADR-003) → Gemini Flash free tier → local Ollama (Qwen) — failover chain |
| Reasoning LLM | Small free daily quota (Gemini) |
| TTS | Groq Orpheus (about 100 requests/hour on the free tier: a hard ceiling with a pre-recorded recovery line; ADR-003) → local Piper / Kokoro → on-screen text. Development and automated tests use a local voice, never Orpheus |
| Data | SQLite (or local Docker Postgres + Redis) |
| Hosting | Your PC + Tailscale / Cloudflare Tunnel for phone access |
| Search / weather | Open-Meteo + a free-tier search API |
| Observability | Local JSONL traces |

Free-profile rules: preemptive generation **off** (it burns request quota), 429s handled with a spoken recovery line, daily request counter in telemetry (plus an hourly TTS counter). Using Groq for STT and TTS is a documented Profile A deviation (ADR-003) chosen for streaming latency; all calls share one account's quotas, so count actual API calls and read the provider's rate-limit headers.

---

## 3. Profile B (premium) — layer-by-layer for maximum performance

*Prices and latencies below come from vendor pages and independent comparisons read in mid-2026. Vendor "time-to-first-byte" claims are usually best-case; independent "time-to-first-audio" numbers are higher. Treat everything as a shortlist and **benchmark on your own corpus from your deployment region**.*

| # | Layer | Free (A) → Premium (B) primary | Alternates worth benchmarking | What it buys | Trigger to upgrade |
|---|---|---|---|---|---|
| 1 | **Transport + agent hosting** | Build + own PC → **LiveKit Cloud Ship ($50/mo)**: 5,000 agent-minutes then $0.01/min, 20 concurrent sessions, **cold-start prevention**, instant rollback; agent deployed in **Mumbai (ap-south)** | Self-host LiveKit + agent on a small Mumbai VM; Scale ($500) only beyond ~20 concurrent | Removes 10–20 s cold starts; agent sits next to your model endpoints; always on | PC uptime unacceptable, or agent-join delay > 2 s, or network RTT to agent > 100 ms |
| 2 | **Turn detection + STT** | Silero + turn-detector + Whisper/Inference credits → **Deepgram Flux** (STT with integrated end-of-turn detection; median EOT under ~300 ms; enables eager EOT + preemptive generation) | ElevenLabs Scribe v2 Realtime (best independent accuracy, ~0.14 s after speech end), Cartesia Ink-2, Deepgram Nova-3 (~$0.005–0.008/min streaming), Sarvam for Indic/code-mixed | Biggest controllable slice of latency; saves an estimated 200–600 ms vs STT + separate VAD | End-of-turn decision p50 > 450 ms, or entity WER on your corpus > target |
| 3 | **TTS** | Piper/Kokoro → **Cartesia Sonic-3.5** or **ElevenLabs Flash v2.5** (~$39–50 per 1M chars) | Gradium (lowest measured p50 and tightest spread in one independent test), Deepgram Aura-2 (cheapest, slower), Inworld TTS-1.5 Mini | Fast, natural first audio; 42 languages incl. Indian languages (Cartesia) | TTS first-audio p50 > 300 ms, or voice quality fails your listening test |
| 4 | **Fast LLM** | Groq/Gemini free → **Groq Developer tier** (raised rate limits) or **Cerebras** — open-weight models with ~120–150 ms median TTFT in one mid-2026 comparison | Gemini Flash-tier with thinking at minimum; **Claude Haiku 5.5** (`claude-haiku-5-5`) for accuracy-critical tool calls | Low, stable TTFT without 429s; prompt caching | 429s on > 1 % of turns, or TTFT p95 > 700 ms |
| 5 | **Reasoning LLM (Tier 2)** | Tiny free quota → **Claude Sonnet 5.5** (`claude-sonnet-5-5`) or **Opus 5.5** (`claude-opus-5-5`) | Gemini Pro-tier | Deep analysis, research synthesis, hard tool plans (spoken hand-off, so latency is not critical) | Free quota exhausted or answer quality insufficient |
| 6 | **Voice isolation / noise** | Build-plan noise cancellation → LiveKit **voice isolation** (1,000 min included on Ship, then $0.0012/min) | Krisp-style client-side isolation | Cleaner STT in noisy rooms and on speakerphone | STT entity WER much worse in the noisy corpus subset |
| 7 | **Database + cache** | SQLite / local containers → **managed PostgreSQL + pgvector** and **fixed-price managed Redis** in the same region as the agent | Self-managed on a VM | Durability, backups, private networking, no PC dependency | Need multi-device access, or backups/uptime matter |
| 8 | **Gateway + workers hosting** | Your PC → always-on containers in the agent's region (small instance is enough for a long time) | Fly.io / Render / VPS / cloud VM | Uptime, reachable from phone without tunnels | Frequent downtime or tunnel friction |
| 9 | **Search / data APIs** | Free search tier + Open-Meteo → paid search API with higher limits and Maps Platform | Provider-specific news/finance APIs | Reliability, fewer rate-limit failures | Tool failure rate > 2 % from limits |
| 10 | **Observability** | Local JSONL → OpenTelemetry + Grafana (or Langfuse for LLM traces), latency alerts | Datadog (costly) | p50/p95 per stage, cost per turn, alerting | Need alerts or long-term trends |
| 11 | **Speech-to-speech mode** *(optional experiment)* | — → OpenAI Realtime, Gemini Live, or Amazon Nova Sonic for chit-chat only | — | Lowest end-to-end latency and most natural feel when a transcript isn't load-bearing | Only after 1–4 are done and you still want lower latency for casual talk |
| 12 | **Embeddings** | FastEmbed local — **keep it** | Hosted embeddings only if measured quality demands | Already free and fast; no network hop | Retrieval quality below target |
| 13 | **Secrets / security** | `.env` → managed secrets manager + KMS-backed token encryption | — | Required before other users or real OAuth tokens in the cloud | Before any hosted deployment holding personal tokens |

**Note on speech-to-speech (row 11):** cascaded STT → LLM → TTS remains the right default for Baby because tool gating, confirmations, verification, and audit logs all need transcripts. Use speech-to-speech only for casual conversation, and route anything that touches tools back through the cascaded pipeline.

---

## 4. Expected premium latency (co-located in Mumbai, all layers upgraded)

| Stage | Premium expectation (p50) |
|---|---|
| Mic → agent transport | 50–80 ms |
| End-of-turn decision (Flux) | ~250–350 ms *(overlapped with LLM via eager EOT)* |
| Router (Tier 0 rules) | < 20 ms |
| LLM time-to-first-token (Groq/Cerebras, thinking off) | 120–250 ms |
| TTS first audio (Cartesia/ElevenLabs/Gradium) | 150–300 ms *(independent measurements; vendor claims are lower)* |
| **Speech-end → first audio, fast path** | **≈ 500–750 ms** *(my composite estimate — verify with your harness)* |
| **Tier-0 (math, time, timers)** | **≈ 300–450 ms** |
| **Barge-in to silence** | **≤ 250 ms** |

**Honest ceiling:** "zero latency" is not physically reachable. End-of-turn detection alone needs ~250–350 ms to be sure you've finished, and natural human turn gaps are around 200 ms. Under ~700 ms feels instant in practice; getting below ~500 ms needs eager end-of-turn, preemptive generation, region co-location, and clause-level TTS all working together.

---

## 5. Upgrade order (best latency gain per dollar first)

1. **Co-location and hosting** — deploy the agent in Mumbai next to your model endpoints (Row 1). Often the biggest free-ish win.
2. **Turn detection + STT** — Flux with eager EOT and preemptive generation (Row 2). Re-enable preemptive generation only now, with a cost cap.
3. **TTS** — bake-off, then switch (Row 3). Choose by **p95**, not p50 — tail latency is what users feel.
4. **Fast LLM paid tier** — for rate limits and stable p95 (Row 4).
5. **Managed data in the same region** (Rows 7–8).
6. **Observability and alerts** (Row 10).
7. **Voice isolation** if you use Baby in noisy places (Row 6).
8. **Reasoning tier** (Row 5) — when free quota or quality limits you.
9. **Speech-to-speech experiment** (Row 11) — last, and only for casual chat.

---

## 6. Rough monthly cost of Profile B (personal use)

Assumptions: 1 hour of voice per day (30 h/month), Baby speaking ~40 % of the time, small tool/LLM usage. *List prices, mid-2026; verify.*

| Item | Estimate |
|---|---|
| LiveKit Cloud Ship (includes 5,000 agent-minutes) | $50 |
| STT (streaming, ~1,800 min) | $9–17 |
| TTS (~720 min at roughly $0.035–0.045/min) | $25–32 |
| LLM (fast tier, moderate tokens) | $2–5 |
| Managed Postgres + Redis (small) | varies by vendor |
| **Total (excluding managed data)** | **≈ $85–105 / month** |

Cost levers: skip Ship and run the agent on a small Mumbai VM instead; use the cheaper TTS after benchmarking; keep preemptive generation limited; cap spend per day.

---

## 7. Swap checklist (use for every premium change)

- [ ] Layer is a measured bottleneck (trigger metric hit)
- [ ] Adapter written against current official docs; version pinned
- [ ] Benchmarked A vs B on the corpus from the deployment region (p50, p95, error rate, cost/turn)
- [ ] ADR written with numbers and decision
- [ ] Behind a feature flag; Profile A remains last in the failover chain
- [ ] Spend cap and alerts set; auto-recharge off
- [ ] Golden conversations and latency replay pass
- [ ] Rollback tested (one config change)

---

## 8. Premium-only feature backlog (not part of the base build)

### 8.1 User-defined wake words
**Base version (Profile A and the first release):** one fixed wake word, "Awaken" (config `WAKE_WORD`), plus the per-request name gate for "Daimon" (spec §3.7). No user-editable wake words, no training UI, no per-user wake models.

**Premium version (later):** let users create their own wake phrase. Do not start this until the owner explicitly unlocks it.

Sketch of the feature:
1. The user types or says a phrase.
2. Phrase check: reject phrases that are too short (under about 6 sounds), resemble common words, or are likely to trigger by accident.
3. The user repeats the phrase 5-10 times, in a quiet room and a noisy one (close and about 2 m away).
4. Train or fine-tune a model, then let the user test it live and adjust sensitivity.
5. Show a false-trigger report after a few days so the user can change the phrase.

Design notes:
- Runs on the user's device (browser or phone app), not in the agent, so audio leaves the device only after the phrase is heard.
- Models are per platform and per user; store and sync them in the user profile (Phase 3 data).
- Always-on listening must be opt-in with a clear mic indicator.
- Engine options to benchmark when unlocked: openWakeWord (open-source, Apache 2.0, custom fine-tuning) and Picovoice Porcupine (polished, trained via Picovoice's console; commercial licensing, so check current pricing before building a user-facing training flow on it). Third-party summaries only; verify on your own recordings.

**Prep that is allowed now (cheap, no scaffolding):** keep the wake word and name aliases in config (never hard-coded); put wake-word code behind a `WakeWordEngine` interface; when recording the corpus, capture "Awaken" at about 30 cm and about 2 m so the recordings can serve as test or training data later.
