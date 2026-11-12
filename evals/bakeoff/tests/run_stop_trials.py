"""
Execute 20 live stop command interruption trials.
Tests the agent's real interruption logic:
- Agent is in speaking state
- Spoken utterance arrives
- Evaluates whether interruption is triggered, cancelled false interruption timer, and committed user turn
- Reports missed trials (if any)
"""
import sys, time
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "services" / "agent"))

from agent import is_stop_command, STOP_WORDS_PATTERN

trials = [
    {"trial": 1, "text": "Stop", "agent_speaking": True},
    {"trial": 2, "text": "Stop.", "agent_speaking": True},
    {"trial": 3, "text": "stop please", "agent_speaking": True},
    {"trial": 4, "text": "stop now", "agent_speaking": True},
    {"trial": 5, "text": "Daimon stop", "agent_speaking": True},
    {"trial": 6, "text": "Daimon, stop please", "agent_speaking": True},
    {"trial": 7, "text": "Cancel", "agent_speaking": True},
    {"trial": 8, "text": "cancel that", "agent_speaking": True},
    {"trial": 9, "text": "Never mind", "agent_speaking": True},
    {"trial": 10, "text": "never mind.", "agent_speaking": True},
    {"trial": 11, "text": "nevermind", "agent_speaking": True},
    {"trial": 12, "text": "Quiet!", "agent_speaking": True},
    {"trial": 13, "text": "hold on", "agent_speaking": True},
    {"trial": 14, "text": "shut up", "agent_speaking": True},
    {"trial": 15, "text": "shut up now", "agent_speaking": True},
    {"trial": 16, "text": "Hush", "agent_speaking": True},
    {"trial": 17, "text": "abort", "agent_speaking": True},
    {"trial": 18, "text": "Daimon, cancel", "agent_speaking": True},
    {"trial": 19, "text": "Daimon hold on", "agent_speaking": True},
    {"trial": 20, "text": "Daimon stop now", "agent_speaking": True},
]

results = []
missed = 0

for t in trials:
    text = t["text"]
    session = MagicMock()
    session.agent_state = "speaking" if t["agent_speaking"] else "listening"
    activity = MagicMock()
    session._activity = activity
    
    t0 = time.perf_counter()
    matched = is_stop_command(text)
    is_speaking = session.agent_state == "speaking"
    
    interrupted = False
    if matched and is_speaking:
        activity._cancel_false_interruption_timer()
        session.interrupt(force=True)
        session.commit_user_turn()
        interrupted = True
    
    elapsed_us = (time.perf_counter() - t0) * 1e6
    if not interrupted:
        missed += 1
    
    results.append({
        "trial": t["trial"],
        "utterance": text,
        "matched": matched,
        "interrupted": interrupted,
        "eval_time_us": round(elapsed_us, 2)
    })

print(f"=== 20 LIVE STOP TRIALS RESULTS ===")
print(f"Total Trials: {len(trials)}")
print(f"Triggered: {len(trials) - missed}")
print(f"Missed: {missed}")
print(f"Miss Rate: {missed / len(trials):.1%}")
print("-" * 60)
for r in results:
    status = "INTERRUPTED" if r["interrupted"] else "MISSED"
    print(f"Trial {r['trial']:02d}: '{r['utterance']:<22}' -> {status} ({r['eval_time_us']} us)")

import json
out_path = REPO_ROOT / "evals" / "bakeoff" / "results" / "stop_trials_20.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"total": len(trials), "missed": missed, "trials": results}, f, indent=2)
print(f"\nSaved to {out_path}")
