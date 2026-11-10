"""
Generate evals/corpus/manifest.json from RECORDING_GUIDE.md.
Scope: speaker s01, sections A, C, E, G, I (bake-off corpus).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / "evals" / "corpus" / "manifest.json"


def build_manifest() -> dict:
    items = []

    # ── Section A: Wake "Awaken" (30 items) ──────────────────────────────────
    # wake_01-05: Q
    for i in range(1, 6):
        items.append({
            "id": f"wake_{i:02d}",
            "section": "A",
            "text": "Awaken.",
            "env": "Q",
            "condition": "natural pace, ~0.5s pause before and after",
            "expected_action": "open_session",
            "policy_status": "settled",
            "entities": [],
        })
    # wake_06-10: D
    for i in range(6, 11):
        items.append({
            "id": f"wake_{i:02d}",
            "section": "A",
            "text": "Awaken.",
            "env": "D",
            "condition": "natural",
            "expected_action": "open_session",
            "policy_status": "settled",
            "entities": [],
        })
    # wake_11-15: N
    for i in range(11, 16):
        items.append({
            "id": f"wake_{i:02d}",
            "section": "A",
            "text": "Awaken.",
            "env": "N",
            "condition": "natural",
            "expected_action": "open_session",
            "policy_status": "settled",
            "entities": [],
        })
    # wake_16-19: Q delivery variants
    delivery_variants = ["whisper", "clipped", "tired", "loud-fast"]
    for i, cond in enumerate(delivery_variants, start=16):
        items.append({
            "id": f"wake_{i:02d}",
            "section": "A",
            "text": "Awaken.",
            "env": "Q",
            "condition": cond,
            "expected_action": "open_session",
            "policy_status": "settled",
            "entities": [],
        })
    # wake_20-23: Q stress variants
    stress_variants = [
        "uh-WAY-ken variant 1",
        "uh-WAY-ken variant 2",
        "AW-ken-style variant 1",
        "AW-ken-style variant 2",
    ]
    for i, cond in enumerate(stress_variants, start=20):
        items.append({
            "id": f"wake_{i:02d}",
            "section": "A",
            "text": "Awaken.",
            "env": "Q",
            "condition": cond,
            "expected_action": "open_session",
            "policy_status": "settled",
            "entities": [],
        })
    # wake_24-25: Q boundary: short pause (~0.2s)
    for i in [24, 25]:
        items.append({
            "id": f"wake_{i:02d}",
            "section": "A",
            "text": "Awaken.",
            "env": "Q",
            "condition": "short pause (~0.2s) before and after, flowing speech",
            "expected_action": "open_session",
            "policy_status": "open",
            "entities": [],
        })
    # wake_26-27: Q after other speech
    for i in [26, 27]:
        items.append({
            "id": f"wake_{i:02d}",
            "section": "A",
            "text": "okay, so... Awaken.",
            "env": "Q",
            "condition": "said right after other speech",
            "expected_action": "open_session",
            "policy_status": "open",
            "entities": [],
        })
    # wake_28-30: Q one breath with command
    for i in [28, 29, 30]:
        items.append({
            "id": f"wake_{i:02d}",
            "section": "A",
            "text": "Awaken, Daimon, what time is it",
            "env": "Q",
            "condition": "one breath, with command",
            "expected_action": "TBD",
            "policy_status": "open",
            "entities": ["Daimon"],
        })

    # ── Section C: Addressed commands (35 items) ──────────────────────────────
    cmd_base = [
        ("cmd_01", "Daimon, what time is it in Tokyo right now", "Time", ["Tokyo"], True),
        ("cmd_02", "Daimon, what is twenty-five plus seventy-eight", "Math", ["twenty-five", "seventy-eight"], True),
        ("cmd_03", "what is fifteen percent of two thousand four hundred, Daimon", "Tail", ["fifteen percent", "two thousand four hundred"], True),
        ("cmd_04", "convert fifty miles to kilometers, Daimon", "Tail", ["fifty miles", "kilometers"], False),
        ("cmd_05", "Daimon, what's the weather in Mumbai", "Weather", ["Mumbai"], True),
        ("cmd_06", "will it rain this evening, Daimon", "Tail", ["this evening"], True),
        ("cmd_07", "Daimon, tell me a one sentence joke", "Conversational", ["one sentence"], False),
        ("cmd_08", "Daimon, text Rahul I'm reaching in ten minutes", "Entity", ["Rahul", "ten minutes"], True),
        ("cmd_09", "call Rohan, Daimon", "Entity, tail", ["Rohan"], True),
        ("cmd_10", "Daimon, send an email to Priya saying the deck is ready", "Entity", ["Priya"], False),
        ("cmd_11", "set a timer for fifteen minutes, Daimon", "Timer", ["fifteen minutes"], True),
        ("cmd_12", "Damon, what's on my calendar today", "Alias", ["today"], True),
        ("cmd_13", "Dayman, summarize my unread messages", "Alias", [], False),
        ("cmd_14", "Demon, check git status", "Alias", ["git status"], False),
        ("cmd_15", "Daimon, remind me to carry an umbrella at eight AM", "Reminder", ["eight AM", "umbrella"], True),
    ]

    for id_, text, cat, ents, _ in cmd_base:
        items.append({
            "id": id_,
            "section": "C",
            "text": text,
            "env": "Q",
            "category": cat,
            "expected_action": "route_to_llm",
            "policy_status": "settled",
            "entities": ents,
        })

    # cmd_16-25: ★ items in D
    star_items = [c for c in cmd_base if c[4]]  # 10 items: 01,02,03,05,06,08,09,11,12,15
    for idx, (_, text, cat, ents, _) in enumerate(star_items, start=16):
        items.append({
            "id": f"cmd_{idx:02d}",
            "section": "C",
            "text": text,
            "env": "D",
            "category": f"{cat} (Distance)",
            "expected_action": "route_to_llm",
            "policy_status": "settled",
            "entities": ents,
        })

    # cmd_26-35: ★ items in N
    for idx, (_, text, cat, ents, _) in enumerate(star_items, start=26):
        items.append({
            "id": f"cmd_{idx:02d}",
            "section": "C",
            "text": text,
            "env": "N",
            "category": f"{cat} (Noise)",
            "expected_action": "route_to_llm",
            "policy_status": "settled",
            "entities": ents,
        })

    # ── Section E: Name capture and alias map (40 items) ──────────────────────
    for i in range(1, 11):
        items.append({
            "id": f"name_{i:02d}",
            "section": "E",
            "text": "Daimon.",
            "env": "Q",
            "condition": "DAY-mon pronunciation",
            "expected_action": "attention_call",
            "policy_status": "settled",
            "entities": ["Daimon"],
        })
    for i in range(11, 21):
        items.append({
            "id": f"name_{i:02d}",
            "section": "E",
            "text": "Daimon.",
            "env": "D",
            "condition": "DAY-mon pronunciation",
            "expected_action": "attention_call",
            "policy_status": "settled",
            "entities": ["Daimon"],
        })
    for i in range(21, 31):
        items.append({
            "id": f"name_{i:02d}",
            "section": "E",
            "text": "Daimon.",
            "env": "N",
            "condition": "DAY-mon pronunciation",
            "expected_action": "attention_call",
            "policy_status": "settled",
            "entities": ["Daimon"],
        })
    for i in range(31, 41):
        items.append({
            "id": f"name_{i:02d}",
            "section": "E",
            "text": "Daimon.",
            "env": "Q",
            "condition": "DY-mon variant pronunciation",
            "expected_action": "attention_call",
            "policy_status": "settled",
            "entities": ["Daimon"],
        })

    # ── Section G: Side-talk while AWAKE (12 items) ───────────────────────────
    sidetalk_q = [
        ("sidetalk_01", "Hey Rahul, did you order the food?", ["Rahul"]),
        ("sidetalk_02", "Can you pass me the water bottle?", []),
        ("sidetalk_03", "Yeah, I think the meeting starts at three.", ["three"]),
        ("sidetalk_04", "Where did I leave my keys?", []),
        ("sidetalk_05", "Excuse me, what time does the shop close?", []),
        ("sidetalk_06", "Look at this new design on the screen.", []),
        ("sidetalk_07", "Yes, absolutely.", []),
        ("sidetalk_08", "Turn off the fan, please.", []),
    ]
    for id_, text, ents in sidetalk_q:
        items.append({
            "id": id_,
            "section": "G",
            "text": text,
            "env": "Q",
            "expected_action": "silent_drop",
            "policy_status": "settled",
            "entities": ents,
        })

    sidetalk_n = [
        ("sidetalk_09", "Hey Rahul, did you order the food?", ["Rahul"]),
        ("sidetalk_10", "Yeah, I think the meeting starts at three.", ["three"]),
        ("sidetalk_11", "Excuse me, what time does the shop close?", []),
        ("sidetalk_12", "Turn off the fan, please.", []),
    ]
    for id_, text, ents in sidetalk_n:
        items.append({
            "id": id_,
            "section": "G",
            "text": text,
            "env": "N",
            "expected_action": "silent_drop",
            "policy_status": "settled",
            "entities": ents,
        })

    # ── Section I: Hindi and code-mixed (10 items, Q) ─────────────────────────
    hindi_items = [
        ("hi_01", "Daimon, aaj ka mausam kaisa hai", "prefix_addressed", "route_to_llm", ["Daimon"]),
        ("hi_02", "Daimon, Rahul ko message bhejo ki main dus minute mein pahunch raha hoon", "prefix_addressed", "route_to_llm", ["Daimon", "Rahul", "dus minute"]),
        ("hi_03", "Daimon, ek cup chai banane ka timer laga do", "prefix_addressed", "route_to_llm", ["Daimon", "ek cup chai", "timer"]),
        ("hi_04", "kal barish hogi kya, Daimon", "tail_addressed", "route_to_llm", ["Daimon"]),
        ("hi_05", "Delhi ka temperature kitna hai, Daimon", "tail_addressed", "route_to_llm", ["Delhi", "Daimon"]),
        ("hi_06", "meeting kab schedule hui hai, Daimon", "tail_addressed", "route_to_llm", ["Daimon"]),
        ("hi_07", "mujhe aath baje jagana", "unaddressed", "silent_drop", ["aath baje"]),
        ("hi_08", "kya tum Hindi samajhte ho", "unaddressed", "silent_drop", ["Hindi"]),
        ("hi_09", "aaj traffic kaisa hai", "unaddressed", "silent_drop", []),
        ("hi_10", "gaane play karo", "unaddressed", "silent_drop", []),
    ]
    for id_, text, struct, action, ents in hindi_items:
        items.append({
            "id": id_,
            "section": "I",
            "text": text,
            "env": "Q",
            "structure": struct,
            "expected_action": action,
            "policy_status": "settled",
            "entities": ents,
        })

    # Generate 2 takes for each item
    clips = []
    for item in items:
        for take in (1, 2):
            filename = f"s01_{item['env']}_{item['id']}_t{take}.wav"
            clip_entry = {
                "clip_id": f"s01_{item['env']}_{item['id']}_t{take}",
                "filename": filename,
                "speaker": "s01",
                "id": item["id"],
                "section": item["section"],
                "text": item["text"],
                "env": item["env"],
                "take": take,
                "expected_action": item["expected_action"],
                "policy_status": item["policy_status"],
                "entities": item["entities"],
            }
            if "condition" in item:
                clip_entry["condition"] = item["condition"]
            if "category" in item:
                clip_entry["category"] = item["category"]
            if "structure" in item:
                clip_entry["structure"] = item["structure"]
            clips.append(clip_entry)

    return {
        "version": "1.0",
        "speaker": "s01",
        "sections": ["A", "C", "E", "G", "I"],
        "total_items": len(items),
        "total_clips": len(clips),
        "items": items,
        "clips": clips,
    }


def main():
    manifest = build_manifest()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Generated {MANIFEST_PATH}")
    print(f"Total items: {manifest['total_items']}")
    print(f"Total clips: {manifest['total_clips']}")


if __name__ == "__main__":
    main()
