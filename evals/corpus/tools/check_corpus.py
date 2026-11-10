"""
check_corpus.py: Windows-friendly corpus validation, status, and derivation tool.
Does NOT require ffmpeg. Uses stdlib wave, numpy, and scipy polyphase resampler.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import struct
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np
import scipy.signal as sig

# Pattern: {speaker}_{env}_{id}_t{take}.wav
FILENAME_RE = re.compile(r"^(?P<speaker>[a-zA-Z0-9]+)_(?P<env>[QDN])_(?P<id>[a-zA-Z0-9_]+)_t(?P<take>[1-9]\d*)\.wav$")


def get_audio_info(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as wf:
        nchannels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        duration = nframes / framerate if framerate > 0 else 0.0
        raw_bytes = wf.readframes(nframes)
    return {
        "nchannels": nchannels,
        "sampwidth": sampwidth,
        "framerate": framerate,
        "nframes": nframes,
        "duration": duration,
        "raw_bytes": raw_bytes,
    }


def compute_audio_stats(raw_bytes: bytes, sampwidth: int) -> dict[str, Any]:
    if not raw_bytes or sampwidth not in (2, 3, 4):
        return {"peak": 0.0, "peak_dBFS": -999.0, "is_clipped": False, "rms_dBFS": -999.0}

    if sampwidth == 2:
        samples = np.frombuffer(raw_bytes, dtype="<i2").astype(np.float64)
        max_val = 32768.0
        clip_thresh = 32760.0
    elif sampwidth == 3:
        b = np.frombuffer(raw_bytes, dtype=np.uint8)
        n_samples = len(b) // 3
        b = b[: n_samples * 3].reshape(-1, 3)
        samples = (
            b[:, 0].astype(np.int32)
            | (b[:, 1].astype(np.int32) << 8)
            | (b[:, 2].astype(np.int8).astype(np.int32) << 16)
        ).astype(np.float64)
        max_val = 8388608.0
        clip_thresh = 8388500.0
    elif sampwidth == 4:
        samples = np.frombuffer(raw_bytes, dtype="<i4").astype(np.float64)
        max_val = 2147483648.0
        clip_thresh = 2147483000.0
    else:
        return {"peak": 0.0, "peak_dBFS": -999.0, "is_clipped": False, "rms_dBFS": -999.0}

    if len(samples) == 0:
        return {"peak": 0.0, "peak_dBFS": -999.0, "is_clipped": False, "rms_dBFS": -999.0}

    abs_samples = np.abs(samples)
    peak = float(np.max(abs_samples))
    is_clipped = bool(peak >= clip_thresh)
    peak_dBFS = float(20.0 * math.log10(peak / max_val)) if peak > 0 else -999.0

    rms = float(np.sqrt(np.mean(samples**2)))
    rms_dBFS = float(20.0 * math.log10(rms / max_val)) if rms > 0 else -999.0

    return {
        "peak": peak,
        "peak_dBFS": peak_dBFS,
        "is_clipped": is_clipped,
        "rms_dBFS": rms_dBFS,
    }


def unpack_pcm(raw_bytes: bytes, sampwidth: int, nchannels: int) -> np.ndarray:
    """Unpack PCM bytes into float64 numpy array in range [-1.0, 1.0]."""
    if sampwidth == 2:
        samples = np.frombuffer(raw_bytes, dtype="<i2").astype(np.float64) / 32768.0
    elif sampwidth == 3:
        b = np.frombuffer(raw_bytes, dtype=np.uint8)
        n_samples = len(b) // 3
        b = b[: n_samples * 3].reshape(-1, 3)
        samples = (
            b[:, 0].astype(np.int32)
            | (b[:, 1].astype(np.int32) << 8)
            | (b[:, 2].astype(np.int8).astype(np.int32) << 16)
        ).astype(np.float64) / 8388608.0
    elif sampwidth == 4:
        samples = np.frombuffer(raw_bytes, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth} bytes")

    if nchannels > 1:
        samples = samples.reshape(-1, nchannels).mean(axis=1)
    return samples


def resample_to_16k(audio_float: np.ndarray, in_rate: int) -> np.ndarray:
    """Resample 1D float audio to 16 kHz using scipy polyphase Kaiser FIR filter."""
    if in_rate == 16000:
        return audio_float
    gcd = math.gcd(16000, in_rate)
    up = 16000 // gcd
    down = in_rate // gcd
    return sig.resample_poly(audio_float, up, down)


def check_room_tone(raw_bytes: bytes, framerate: int, sampwidth: int, duration: float) -> tuple[bool, str]:
    """Check if the first 0.5s and last 0.5s resemble room tone (RMS < -30 dBFS)."""
    if duration < 1.0:
        return False, f"Duration {duration:.2f}s is too short for 0.5s lead/trail room tone"

    bytes_per_sec = framerate * sampwidth
    lead_bytes = raw_bytes[: int(0.5 * bytes_per_sec)]
    trail_bytes = raw_bytes[-int(0.5 * bytes_per_sec) :]

    lead_stats = compute_audio_stats(lead_bytes, sampwidth)
    trail_stats = compute_audio_stats(trail_bytes, sampwidth)

    # Lead/trail should be quiet (RMS <= -30 dBFS)
    warns = []
    if lead_stats["rms_dBFS"] > -30.0:
        warns.append(f"lead room tone loud (RMS {lead_stats['rms_dBFS']:.1f} dBFS > -30 dBFS)")
    if trail_stats["rms_dBFS"] > -30.0:
        warns.append(f"trail room tone loud (RMS {trail_stats['rms_dBFS']:.1f} dBFS > -30 dBFS)")

    if warns:
        return False, "; ".join(warns)
    return True, "OK"


# ── Subcommand: validate ─────────────────────────────────────────────────────

def run_validate(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}", file=sys.stderr)
        return 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    manifest_ids = {item["id"] for item in manifest.get("items", [])}
    manifest_clips = {clip["filename"]: clip for clip in manifest.get("clips", [])}

    target_dir = Path(args.dir)
    if not target_dir.exists():
        print(f"Directory {target_dir} does not exist.")
        return 0

    wav_files = sorted(target_dir.glob("*.wav"))
    if not wav_files:
        print(f"No WAV files found in {target_dir}")
        return 0

    errors = 0
    warnings = 0

    mode = args.mode.lower()
    print(f"=== Validating {len(wav_files)} WAV files in {target_dir} (mode: {mode}) ===")

    for wav_path in wav_files:
        fname = wav_path.name
        match = FILENAME_RE.match(fname)
        file_errors = []
        file_warnings = []

        if not match:
            file_errors.append(f"Filename does not match pattern {{speaker}}_{{env}}_{{id}}_t{{take}}.wav")
        else:
            item_id = match.group("id")
            if item_id not in manifest_ids:
                file_errors.append(f"Item ID '{item_id}' not found in manifest")
            if fname not in manifest_clips:
                file_warnings.append(f"Filename '{fname}' not listed in manifest clips")

        try:
            info = get_audio_info(wav_path)
            framerate = info["framerate"]
            nchannels = info["nchannels"]
            sampwidth = info["sampwidth"]
            duration = info["duration"]
            raw_bytes = info["raw_bytes"]

            if mode == "master":
                if framerate < 48000:
                    file_errors.append(f"Master framerate must be >= 48000 Hz, got {framerate} Hz")
                if nchannels != 1:
                    file_errors.append(f"Master must be mono (1 channel), got {nchannels}")
                if sampwidth < 2:
                    file_errors.append(f"Master bit depth must be >= 16-bit (>= 2 bytes), got {sampwidth * 8}-bit")
            elif mode == "derived":
                if framerate != 16000:
                    file_errors.append(f"Derived framerate must be exactly 16000 Hz, got {framerate} Hz")
                if nchannels != 1:
                    file_errors.append(f"Derived must be mono (1 channel), got {nchannels}")
                if sampwidth != 2:
                    file_errors.append(f"Derived bit depth must be exactly 16-bit (2 bytes), got {sampwidth * 8}-bit")

            # Clipping check -> ERROR
            stats = compute_audio_stats(raw_bytes, sampwidth)
            if stats["is_clipped"]:
                file_errors.append(f"Audio is clipped! Peak reached {stats['peak']:.0f}")

            # Peak dBFS check -> WARN if outside -18 to -3 dBFS
            peak_db = stats["peak_dBFS"]
            if peak_db < -18.0 or peak_db > -3.0:
                file_warnings.append(f"Peak dBFS {peak_db:.1f} is outside recommended range [-18, -3] dBFS")

            # Duration check -> WARN on odd duration (< 1.0s or > 25.0s)
            if duration < 1.0:
                file_warnings.append(f"Short duration: {duration:.2f}s (< 1.0s)")
            elif duration > 25.0:
                file_warnings.append(f"Long duration: {duration:.2f}s (> 25.0s)")

            # Lead/trail room tone check -> WARN
            rt_ok, rt_msg = check_room_tone(raw_bytes, framerate, sampwidth, duration)
            if not rt_ok:
                file_warnings.append(f"Room tone check: {rt_msg}")

        except Exception as ex:
            file_errors.append(f"Failed to read WAV file: {ex}")

        if file_errors:
            errors += len(file_errors)
            for err in file_errors:
                print(f"  [ERROR] {fname}: {err}")
        if file_warnings:
            warnings += len(file_warnings)
            for w in file_warnings:
                print(f"  [WARN]  {fname}: {w}")

    print(f"\nValidation complete: {errors} error(s), {warnings} warning(s).")
    return 1 if errors > 0 else 0


# ── Subcommand: status ───────────────────────────────────────────────────────

def run_status(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}", file=sys.stderr)
        return 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    target_dir = Path(args.dir)
    existing_files = set(p.name for p in target_dir.glob("*.wav")) if target_dir.exists() else set()

    clips = manifest.get("clips", [])
    total_expected = len(clips)
    total_found = sum(1 for c in clips if c["filename"] in existing_files)

    print(f"=== Corpus Coverage Status ({target_dir}) ===")
    print(f"Total Clips Expected: {total_expected}")
    print(f"Total Clips Found:    {total_found} ({total_found / total_expected * 100:.1f}%)" if total_expected else "No clips expected")

    # Group by section and environment
    by_sec_env: dict[tuple[str, str], list[dict]] = {}
    for c in clips:
        key = (c["section"], c["env"])
        by_sec_env.setdefault(key, []).append(c)

    print("\nCoverage Breakdown by Section & Environment:")
    missing_clips = []
    for (sec, env), group in sorted(by_sec_env.items()):
        found = sum(1 for c in group if c["filename"] in existing_files)
        total = len(group)
        pct = found / total * 100 if total else 0
        print(f"  Section {sec} [{env}]: {found:3d}/{total:3d} ({pct:5.1f}%)")
        for c in group:
            if c["filename"] not in existing_files:
                missing_clips.append(c["filename"])

    if missing_clips:
        print(f"\nMissing Clips ({len(missing_clips)}):")
        for m in missing_clips[:30]:
            print(f"  - {m}")
        if len(missing_clips) > 30:
            print(f"  ... and {len(missing_clips) - 30} more.")
    else:
        print("\nAll expected clips are present!")

    return 0


# ── Subcommand: derive ───────────────────────────────────────────────────────

def run_derive(args: argparse.Namespace) -> int:
    masters_dir = Path(args.masters_dir)
    wavs_dir = Path(args.wavs_dir)

    if not masters_dir.exists():
        print(f"Masters directory {masters_dir} does not exist.")
        return 0

    wavs_dir.mkdir(parents=True, exist_ok=True)
    master_files = sorted(masters_dir.glob("*.wav"))

    if not master_files:
        print(f"No master WAV files found in {masters_dir}")
        return 0

    derived_count = 0
    skipped_count = 0
    errors = 0

    print(f"Deriving 16 kHz mono 16-bit WAVs from {masters_dir} -> {wavs_dir}...")

    for master_path in master_files:
        out_path = wavs_dir / master_path.name

        if out_path.exists() and not args.force:
            skipped_count += 1
            continue

        try:
            with wave.open(str(master_path), "rb") as in_wf:
                in_channels = in_wf.getnchannels()
                in_width = in_wf.getsampwidth()
                in_rate = in_wf.getframerate()
                nframes = in_wf.getnframes()
                raw_bytes = in_wf.readframes(nframes)

            # 1. Unpack to float mono [-1.0, 1.0]
            audio_mono = unpack_pcm(raw_bytes, in_width, in_channels)

            # 2. Resample to 16 kHz using scipy polyphase Kaiser FIR filter
            audio_16k = resample_to_16k(audio_mono, in_rate)

            # 3. Quantize to 16-bit PCM
            audio_int16 = np.clip(np.round(audio_16k * 32767.0), -32768, 32767).astype("<i2")

            # 4. Write derived file
            with wave.open(str(out_path), "wb") as out_wf:
                out_wf.setnchannels(1)
                out_wf.setsampwidth(2)
                out_wf.setframerate(16000)
                out_wf.writeframes(audio_int16.tobytes())

            derived_count += 1

        except Exception as ex:
            print(f"ERROR deriving {master_path.name}: {ex}", file=sys.stderr)
            errors += 1

    print(f"Derive complete: {derived_count} derived, {skipped_count} skipped (already existed), {errors} error(s).")
    return 1 if errors > 0 else 0


# ── Main CLI ─────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Corpus check, validation, and derivation tool.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Show coverage vs manifest")
    p_status.add_argument("--dir", default="evals/corpus/wavs", help="Directory with WAV files (default: evals/corpus/wavs)")
    p_status.add_argument("--manifest", default="evals/corpus/manifest.json", help="Path to manifest.json")

    # validate
    p_val = subparsers.add_parser("validate", help="Validate WAV format, levels, clipping, room tone")
    p_val.add_argument("--dir", default="evals/corpus/wavs", help="Directory with WAV files")
    p_val.add_argument("--mode", choices=["master", "derived"], default="derived", help="Validation mode")
    p_val.add_argument("--manifest", default="evals/corpus/manifest.json", help="Path to manifest.json")

    # derive
    p_der = subparsers.add_parser("derive", help="Derive 16 kHz mono 16-bit WAVs from masters")
    p_der.add_argument("--masters-dir", default="evals/corpus/masters", help="Directory with master WAVs")
    p_der.add_argument("--wavs-dir", default="evals/corpus/wavs", help="Output directory for derived WAVs")
    p_der.add_argument("--force", action="store_true", help="Overwrite existing derived WAVs")

    args = parser.parse_args()
    if args.command == "status":
        return run_status(args)
    elif args.command == "validate":
        return run_validate(args)
    elif args.command == "derive":
        return run_derive(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
