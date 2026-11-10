"""
make_script.py: Generates an ordered recording script (Markdown + CSV) from manifest.json.

Ordered blocks:
  1. Environment Q (Quiet): sections ordered C, E, I, G, A
  2. Environment D (Desk): sections ordered C, E, A
  3. Environment N (Noisy): sections ordered C, E, G, A

Outputs:
  - evals/corpus/RECORDING_SCRIPT.md
  - evals/corpus/RECORDING_SCRIPT.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


def natural_sort_key(s: str) -> list[int | str]:
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


def generate_scripts(
    manifest_path: Path,
    out_md: Path,
    out_csv: Path,
) -> int:
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}", file=sys.stderr)
        return 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    clips: list[dict[str, Any]] = manifest.get("clips", [])
    if len(clips) != 254:
        print(f"WARNING: Expected 254 clips, got {len(clips)} in manifest", file=sys.stderr)

    # Blocks definition
    env_blocks = [
        ("Q", "Quiet room, headset or close mic (natural pace, ~1s room tone lead/trail)", ["C", "E", "I", "G", "A"]),
        ("D", "Desk: laptop built-in mic, speaker 1-2 m away", ["C", "E", "A"]),
        ("N", "Noisy: fan, background music or TV at realistic volume", ["C", "E", "G", "A"]),
    ]

    all_ordered_clips: list[tuple[int, dict[str, Any]]] = []
    block_clips: dict[str, list[dict[str, Any]]] = {}

    global_order = 1
    for env_code, _, section_order in env_blocks:
        env_clips = [c for c in clips if c.get("env") == env_code]
        ordered_for_block: list[dict[str, Any]] = []

        for sec in section_order:
            sec_clips = [c for c in env_clips if c.get("section") == sec]
            # Sort by item id naturally, then take
            sec_clips.sort(key=lambda c: (natural_sort_key(c.get("id", "")), c.get("take", 1)))
            ordered_for_block.extend(sec_clips)

        # Catch any unexpected section not listed
        remaining = [c for c in env_clips if c.get("section") not in section_order]
        remaining.sort(key=lambda c: (c.get("section", ""), natural_sort_key(c.get("id", "")), c.get("take", 1)))
        ordered_for_block.extend(remaining)

        block_clips[env_code] = ordered_for_block
        for c in ordered_for_block:
            all_ordered_clips.append((global_order, c))
            global_order += 1

    # Total verification
    total_ordered = len(all_ordered_clips)
    print(f"Total clips ordered: {total_ordered} (Manifest total: {len(clips)})")
    for env_code, _, sec_order in env_blocks:
        count = len(block_clips[env_code])
        print(f"  Block {env_code}: {count} clips")

    # 1. Write RECORDING_SCRIPT.csv
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "order",
            "filename",
            "env",
            "section",
            "item_id",
            "take",
            "text",
            "delivery_note",
            "checked",
        ])
        for order, c in all_ordered_clips:
            writer.writerow([
                order,
                c.get("filename", ""),
                c.get("env", ""),
                c.get("section", ""),
                c.get("id", ""),
                c.get("take", 1),
                c.get("text", ""),
                c.get("condition", ""),
                "[ ]",
            ])
    print(f"Wrote CSV script to {out_csv}")

    # 2. Write RECORDING_SCRIPT.md
    out_md.parent.mkdir(parents=True, exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# Daimon Bake-Off Recording Script (Speaker s01)\n\n")
        f.write(f"Total Clips: **{total_ordered}** (exact 127 items × 2 takes = 254 clips).\n\n")
        f.write("## Recording Rules & Checklist\n")
        f.write("- **Format**: 48 kHz, mono, 24-bit PCM master WAVs (`evals/corpus/masters/`).\n")
        f.write("- **Name Pronunciations**:\n")
        f.write("  - **Daimon**: Pronounce as **DAY-mon** (/ˈdeɪmɒn/) in all lines except `name_31–40`.\n")
        f.write("  - **name_31–40**: Deliberately pronounce as **DY-mon** (/ˈdaɪmɒn/) variant.\n")
        f.write("  - **Damon** (cmd_12): Pronounce as **DAY-mun** (/ˈdeɪmən/).\n")
        f.write("  - **Dayman** (cmd_13): Pronounce as **DAY-man** (/ˈdeɪmæn/).\n")
        f.write("  - **Demon** (cmd_14): Pronounce as **DEE-mon** (/ˈdiːmən/).\n")
        f.write("- **Side-talk (Section G)**: Speak to an imaginary person sitting nearby in the room, turning slightly away from the mic.\n")
        f.write("- **Microphone Selection**:\n")
        f.write("  - Use one consistent microphone for all of Block Q (wired headset or close USB/XLR mic).\n")
        f.write("  - Use the laptop's built-in microphone for Block D (you sit 1–2 m away from the laptop).\n")
        f.write("  - Note the exact device names used for ground-truth metadata logging.\n")
        f.write("- **Noise Consistency (Block N)**: Keep background fan, TV, or noise source at a fixed, constant volume for the entire N block.\n")
        f.write("- **Environment checklist**:\n")
        f.write("  - Windows Sound Settings: Set default recording device to **48000 Hz (24-bit or 16-bit Studio Quality)**.\n")
        f.write("  - Turn **OFF** Audio Enhancements, Noise Suppression, and Automatic Gain Control (AGC) in Windows Sound Properties and in OEM software (Realtek, Dell Optimizer, Waves MaxxAudio, etc.).\n")
        f.write("  - **NO Bluetooth microphones** (Bluetooth drops to 8/16 kHz mono telephony profiles; use wired USB or analog XLR/3.5mm).\n")
        f.write("  - Close any apps that use or process mic audio (Teams, Zoom, Discord, Slack, browser tabs).\n")
        f.write("- **Lead / Trail room tone**: Leave ~1 second of ambient silence before speaking and after speaking each line.\n")
        f.write("- **Levels**: Peaks between -18 and -3 dBFS; **zero clipping** (clipping requires retake).\n")
        f.write("- **Order**: Complete Block Q first (Sections C, E, I, G, A), then Block D, then Block N.\n\n")

        for env_code, env_desc, sec_order in env_blocks:
            b_clips = block_clips[env_code]
            f.write(f"## Block {env_code}: {env_desc}\n\n")
            f.write(f"**Total clips in this block: {len(b_clips)}** (Sections: {', '.join(sec_order)})\n\n")
            f.write("| # | Filename | Text to say | Delivery Note / Condition | Done |\n")
            f.write("|---|---|---|---|:---:|\n")
            for order, c in all_ordered_clips:
                if c.get("env") == env_code:
                    clean_text = c.get("text", "").replace("|", "\\|")
                    clean_cond = c.get("condition", "").replace("|", "\\|")
                    f.write(f"| {order} | `{c.get('filename')}` | **{clean_text}** | {clean_cond} | [ ] |\n")
            f.write("\n---\n\n")

    print(f"Wrote Markdown script to {out_md}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ordered recording script for speaker s01.")
    parser.add_argument("--manifest", default=str(REPO_ROOT / "evals" / "corpus" / "manifest.json"))
    parser.add_argument("--out-md", default=str(REPO_ROOT / "evals" / "corpus" / "RECORDING_SCRIPT.md"))
    parser.add_argument("--out-csv", default=str(REPO_ROOT / "evals" / "corpus" / "RECORDING_SCRIPT.csv"))
    args = parser.parse_args()

    return generate_scripts(
        manifest_path=Path(args.manifest),
        out_md=Path(args.out_md),
        out_csv=Path(args.out_csv),
    )


if __name__ == "__main__":
    sys.exit(main())
