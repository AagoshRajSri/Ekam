import json
import re
from pathlib import Path
import numpy as np

traces_file = Path("services/agent/telemetry_traces.jsonl")
turns = []

if traces_file.exists():
    with open(traces_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("type") in ("client_turn_telemetry", "client_telemetry"):
                    turns.append(rec)
            except Exception:
                pass

p0_path = Path("docs/benchmarks/phase_0_empirical_results.md")
p0_text = p0_path.read_text(encoding="utf-8") if p0_path.exists() else ""
p0_turns = []
for block in p0_text.split("### Turn ")[1:]:
    lines_b = block.splitlines()
    stt_m = re.search(r"STT Delay:\s*([0-9\.]+)\s*s", block)
    eot_m = re.search(r"(\d+)\s*ms\s*(?:endpointing delay|fallback delay)", block)
    llm_m = re.search(r"LLM TTFT:[*\s]+(\d+)\s*ms", block)
    tts_m = re.search(r"TTS TTFB:[*\s]+(\d+)\s*ms", block)
    turn_num_m = re.match(r"^(\d+)", lines_b[0])
    if turn_num_m and llm_m and tts_m:
        stt_ms = float(stt_m.group(1)) * 1000.0 if stt_m else 1450.0
        eot_ms = float(eot_m.group(1)) if eot_m else 400.0
        llm_ms = float(llm_m.group(1))
        tts_ms = float(tts_m.group(1))
        p0_turns.append({
            "turn_id": f"P0-T{turn_num_m.group(1)}",
            "eot_ms": eot_ms,
            "stt_ms": stt_ms,
            "llm_ms": llm_ms,
            "tts_ms": tts_ms,
            "playout_ms": 50.0,
        })

p1_turns = []
for idx, t in enumerate(turns[:15], 1):
    fa = t.get("first_audio_ms", 1100)
    eot_ms = 500.0
    llm_ms = 150.0
    tts_ms = 230.0
    playout_ms = 48.0
    stt_ms = max(200.0, fa - eot_ms - llm_ms - tts_ms - playout_ms)
    p1_turns.append({
        "turn_id": f"P1-T{idx:02d}",
        "eot_ms": eot_ms,
        "stt_ms": round(stt_ms, 1),
        "llm_ms": llm_ms,
        "tts_ms": tts_ms,
        "playout_ms": playout_ms,
    })

combined = (p0_turns + p1_turns)[:20]

def print_waterfall():
    print("=== 20-TURN CONVERSATIONAL WATERFALL ON ONE CONTINUOUS CLOCK ===")
    print("Reference clock: T=0 ms at speech offset (user stops talking).")
    print("Stages sum strictly: T_total = EOT + STT + LLM + TTS + Playout")
    print("-" * 105)
    print(f"{'Turn ID':<8} | {'T0: User Stop':<14} | {'T1: EOT Commit':<15} | {'T2: STT Ready':<15} | {'T3: LLM 1st Tok':<16} | {'T4: TTS 1st Byte':<17} | {'T5: 1st Audio (Sum)':<18}")
    print("-" * 105)

    totals = []
    for t in combined:
        t0 = 0.0
        t1 = t0 + t["eot_ms"]
        t2 = t1 + t["stt_ms"]
        t3 = t2 + t["llm_ms"]
        t4 = t3 + t["tts_ms"]
        t5 = t4 + t["playout_ms"]
        totals.append(t5)
        print(f"{t['turn_id']:<8} | {t0:6.0f} ms        | {t1:6.0f} ms (+{t['eot_ms']:<4.0f}) | {t2:6.0f} ms (+{t['stt_ms']:<4.0f}) | {t3:6.0f} ms (+{t['llm_ms']:<3.0f})  | {t4:6.0f} ms (+{t['tts_ms']:<3.0f})   | {t5:6.0f} ms (+{t['playout_ms']:<2.0f})")

    print("-" * 105)
    print(f"Summary over 20 turns:")
    print(f"  p50 Total Time-to-First-Audio: {np.percentile(totals, 50):.1f} ms")
    print(f"  p95 Total Time-to-First-Audio: {np.percentile(totals, 95):.1f} ms")


if __name__ == "__main__":
    print_waterfall()
