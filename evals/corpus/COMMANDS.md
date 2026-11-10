# Daimon Corpus & Bake-off Command Reference

All commands below are designed to run copy-paste from the repository root (`c:\Aagosh\CODE\Ekam`) using `uv run --project services/agent`.

> [!NOTE]
> Do NOT use `uv run --directory services/agent`, as that changes the working directory into `services/agent` and breaks repo-relative file paths. Always use `--project services/agent`.

---

## 1. Environment & Setup

Verify Python 3.12 and dependencies:
```powershell
uv sync --project services/agent
```

Verify installed candidate audio/DSP libraries:
```powershell
uv run --project services/agent python -c "import scipy, sounddevice, numpy, yaml, kokoro_onnx; print('All dependencies verified')"
```

---

## 2. Recording Script Generation

Regenerate the ordered recording checklist (`RECORDING_SCRIPT.md` + `RECORDING_SCRIPT.csv`) from `manifest.json`:
```powershell
uv run --project services/agent python evals/corpus/tools/make_script.py
```

Outputs:
* `evals/corpus/RECORDING_SCRIPT.md` (Markdown script with check boxes and block tables)
* `evals/corpus/RECORDING_SCRIPT.csv` (CSV script formatted for logging)

---

## 3. Recorder CLI (`record_session.py`)

### List Available Microphones
```powershell
uv run --project services/agent python evals/corpus/tools/record_session.py --list-devices
```

### Record Quiet Room Block (Q)
```powershell
uv run --project services/agent python evals/corpus/tools/record_session.py --env Q
```

### Record Desk Distance Block (D)
```powershell
uv run --project services/agent python evals/corpus/tools/record_session.py --env D
```

### Record Noisy Background Block (N)
```powershell
uv run --project services/agent python evals/corpus/tools/record_session.py --env N
```

### Record Specific Section (e.g. Hindi Section I)
```powershell
uv run --project services/agent python evals/corpus/tools/record_session.py --sections I
```

### Re-record an Existing Clip (Overwrite Mode)
```powershell
uv run --project services/agent python evals/corpus/tools/record_session.py --overwrite --sections C
```

**Key Controls During Recording Session:**
* `Enter` : Start recording / Stop recording
* `Enter` : Accept & save 48 kHz mono 24-bit WAV to `evals/corpus/masters/`
* `r`     : Redo take (logs technical fault to `evals/corpus/quality_flags.json`)
* `p`     : Playback recorded audio through speakers
* `s`     : Skip this clip
* `q`     : Quit session cleanly (resumable anytime)

---

## 4. Corpus Status, Validation, and Derivation

### Check Recording Progress vs Manifest
```powershell
uv run --project services/agent python evals/corpus/tools/check_corpus.py status --dir evals/corpus/masters
```

### Validate 48 kHz 24-bit Master Files
Checks 48 kHz sample rate, mono channel, clipping errors, levels within -18 to -3 dBFS, and ~1s room tone:
```powershell
uv run --project services/agent python evals/corpus/tools/check_corpus.py validate --dir evals/corpus/masters --mode master
# Shortcut:
uv run --project services/agent python evals/corpus/tools/check_corpus.py validate --masters
```

### Derive 16 kHz Mono 16-bit WAVs for Pipeline
Converts masters from `evals/corpus/masters/` to `evals/corpus/wavs/` using polyphase anti-alias filtering (never overwrites unless `--force` is passed):
```powershell
uv run --project services/agent python evals/corpus/tools/check_corpus.py derive
```

### Validate 16 kHz Derived Files
```powershell
uv run --project services/agent python evals/corpus/tools/check_corpus.py validate --dir evals/corpus/wavs --mode derived
```

---

## 5. Provider Bake-off Harness

### Dry-run Request & Quota Accounting (Dev Split)
Prints expected request counts per candidate before spending any quota or API calls:
```powershell
uv run --project services/agent python evals/bakeoff/run_bakeoff.py --split dev
```

### Offline Fake Bake-off Run (Zero API Calls)
Executes end-to-end evaluation with local simulated adapters and generates `docs/benchmarks/phase_1_bakeoff.md`:
```powershell
uv run --project services/agent python evals/bakeoff/run_bakeoff.py --split dev --no-dry-run --use-fakes
```

### Live Provider Bake-off on Dev Split (After Recordings Exist)
```powershell
uv run --project services/agent python evals/bakeoff/run_bakeoff.py --split dev --no-dry-run
```

### Final Benchmark on Locked Test Split (Run Once)
Requires explicit `--final` flag; updates `split.lock`:
```powershell
uv run --project services/agent python evals/bakeoff/run_bakeoff.py --split test --final --no-dry-run
```

---

## 6. Automated Test Suites

### Corpus Tools Tests
```powershell
uv run --project services/agent pytest evals/corpus/tools/tests/ -v
```

### Bake-off Harness Tests
```powershell
uv run --project services/agent pytest evals/bakeoff/tests/ -v
```

### Live Agent Unit & Smoke Tests
```powershell
uv run --project services/agent pytest services/agent/tests/test_agent_smoke.py services/agent/tests/test_barge_in.py -v
```

### Opt-in Live LLM Failover & Latency Tests (Requires API Keys / Ollama)
```powershell
$env:RUN_LIVE_LLM_TESTS="1"; uv run --project services/agent pytest services/agent/tests/test_live_llm.py -v -s
```

### Opt-in Live Orpheus Pronunciation Test (Requires Real Groq Key)
```powershell
$env:RUN_LIVE_TTS_TESTS="1"; uv run --project services/agent pytest services/agent/tests/test_orpheus_pronunciation.py -v -s
```

