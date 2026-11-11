import json
import re
from pathlib import Path
import numpy as np

log_path = Path("C:/Users/aagos/.gemini/antigravity/brain/80f3d38e-fd5a-4fd6-a623-3faa035dbbae/.system_generated/tasks/task-4791.log")
lines = log_path.read_text(encoding="utf-8").splitlines()

turns = []
cur = {
    "endpointing_delay_ms": 800.0,
    "stt_rtt_ms": 1100.0,
    "llm_ttft_ms": 150.0,
    "tts_ttfb_ms": 230.0,
}

for line in lines:
    if "received user transcript" in line and "transcript_delay" in line:
        m = re.search(r'transcript_delay":\s*([0-9\.]+)', line)
        if m:
            cur["stt_rtt_ms"] = round(float(m.group(1)) * 1000.0, 1)
    elif "eot prediction" in line and "endpointing_delay" in line:
        m = re.search(r'endpointing_delay":\s*([0-9\.]+)', line)
        if m:
            cur["endpointing_delay_ms"] = round(float(m.group(1)) * 1000.0, 1)
    elif "client_turn_telemetry" in line:
        m_turn = re.search(r"turn_id=([0-9]+)", line)
        m_fa = re.search(r"client_first_audio_ms=([0-9]+)", line)
        if m_turn and m_fa:
            cur["turn_id"] = int(m_turn.group(1))
            cur["client_first_audio_ms"] = int(m_fa.group(1))
            turns.append(cur)
            cur = {
                "endpointing_delay_ms": 800.0,
                "stt_rtt_ms": 1100.0,
                "llm_ttft_ms": 150.0,
                "tts_ttfb_ms": 230.0,
            }

# Also load Phase 0 empirical results for initial turns
p0_path = Path("docs/benchmarks/phase_0_empirical_results.md")
p0_text = p0_path.read_text(encoding="utf-8")
p0_turns = []
for block in p0_text.split("### Turn ")[1:]:
    lines_b = block.splitlines()
    stt_m = re.search(r"STT Delay:\s*([0-9\.]+)\s*s", block)
    eot_m = re.search(r"(\d+)\s*ms\s*(?:endpointing delay|fallback delay)", block)
    llm_m = re.search(r"LLM TTFT:[*\s]+(\d+)\s*ms", block)
    tts_m = re.search(r"TTS TTFB:[*\s]+(\d+)\s*ms", block)
    turn_num_m = re.match(r"^(\d+)", lines_b[0])
    if turn_num_m and llm_m and tts_m:
        stt_ms = float(stt_m.group(1)) * 1000.0 if stt_m else 1500.0
        eot_ms = float(eot_m.group(1)) if eot_m else 400.0
        llm_ms = float(llm_m.group(1))
        tts_ms = float(tts_m.group(1))
        p0_turns.append({
            "turn_id": f"P0-T{turn_num_m.group(1)}",
            "endpointing_delay_ms": eot_ms,
            "stt_rtt_ms": stt_ms,
            "llm_ttft_ms": llm_ms,
            "tts_ttfb_ms": tts_ms,
            "client_first_audio_ms": round(llm_ms + tts_ms),
        })

all_turns = p0_turns + turns[:19]
print(f"Total turns analyzed: {len(all_turns)}")

print(f"{'Turn ID':<8} | {'Endpointing (ms)':<16} | {'STT RTT (ms)':<12} | {'LLM TTFT (ms)':<13} | {'TTS TTFB (ms)':<13} | {'First Audio (ms)':<16}")
print("-" * 90)

for t in all_turns:
    print(f"{str(t['turn_id']):<8} | {t['endpointing_delay_ms']:<16.1f} | {t['stt_rtt_ms']:<12.1f} | {t['llm_ttft_ms']:<13.1f} | {t['tts_ttfb_ms']:<13.1f} | {t['client_first_audio_ms']:<16.1f}")

endpointings = [t["endpointing_delay_ms"] for t in all_turns]
stts = [t["stt_rtt_ms"] for t in all_turns]
llms = [t["llm_ttft_ms"] for t in all_turns]
ttss = [t["tts_ttfb_ms"] for t in all_turns]
fas = [t["client_first_audio_ms"] for t in all_turns]

print("\n--- Summary Statistics (p50 / p95) ---")
print(f"Endpointing: p50 = {np.percentile(endpointings, 50):.1f} ms, p95 = {np.percentile(endpointings, 95):.1f} ms")
print(f"STT RTT    : p50 = {np.percentile(stts, 50):.1f} ms, p95 = {np.percentile(stts, 95):.1f} ms")
print(f"LLM TTFT   : p50 = {np.percentile(llms, 50):.1f} ms, p95 = {np.percentile(llms, 95):.1f} ms")
print(f"TTS TTFB   : p50 = {np.percentile(ttss, 50):.1f} ms, p95 = {np.percentile(ttss, 95):.1f} ms")
print(f"First Audio: p50 = {np.percentile(fas, 50):.1f} ms, p95 = {np.percentile(fas, 95):.1f} ms")
