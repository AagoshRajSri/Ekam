"""
record_session.py: Interactive CLI recorder for the Daimon benchmark corpus.

Captures 48 kHz mono 24-bit PCM master WAVs into evals/corpus/masters/.
Resumable: checks existing masters and only prompts for missing clips.
Provides live peak meter, clipping error check, and [-18, -3] dBFS warning.
Logs technical retakes to evals/corpus/quality_flags.json.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]


# ── Audio Backend Interface (pluggable for tests without microphone) ─────────

class AudioBackend(Protocol):
    def list_devices(self) -> list[dict[str, Any]]:
        ...

    def record(
        self,
        duration_or_stop_event: Any,
        samplerate: int = 48000,
        device: int | str | None = None,
        meter_callback: Any = None,
    ) -> np.ndarray:
        ...

    def play(self, audio: np.ndarray, samplerate: int = 48000) -> None:
        ...


class SoundDeviceBackend:
    def list_devices(self) -> list[dict[str, Any]]:
        import sounddevice as sd
        devices = sd.query_devices()
        return [
            {
                "index": i,
                "name": d["name"],
                "max_input_channels": d["max_input_channels"],
                "default_samplerate": d["default_samplerate"],
            }
            for i, d in enumerate(devices)
            if d.get("max_input_channels", 0) > 0
        ]

    def record(
        self,
        stop_event: Any,
        samplerate: int = 48000,
        device: int | str | None = None,
        meter_callback: Any = None,
    ) -> np.ndarray:
        import sounddevice as sd
        chunks: list[np.ndarray] = []

        def callback(indata, frames, time_info, status):
            if status:
                pass
            chunk = indata.copy().flatten()
            chunks.append(chunk)
            if meter_callback:
                meter_callback(chunk)

        with sd.InputStream(
            samplerate=samplerate,
            channels=1,
            dtype="float32",
            device=device,
            callback=callback,
        ):
            # Record until stop_event is signaled (e.g. Enter pressed or flag set)
            if callable(stop_event):
                while not stop_event():
                    time.sleep(0.05)
            else:
                input()

        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks)

    def play(self, audio: np.ndarray, samplerate: int = 48000) -> None:
        import sounddevice as sd
        sd.play(audio, samplerate=samplerate)
        sd.wait()


class FakeAudioBackend:
    """Mock audio backend for unit tests (zero hardware dependency)."""

    def __init__(self, fake_audio: np.ndarray | None = None) -> None:
        self.recorded_count = 0
        self.played_count = 0
        self._fake_audio = fake_audio

    def list_devices(self) -> list[dict[str, Any]]:
        return [
            {"index": 0, "name": "Fake Mock Mic", "max_input_channels": 1, "default_samplerate": 48000.0}
        ]

    def record(
        self,
        stop_event: Any,
        samplerate: int = 48000,
        device: int | str | None = None,
        meter_callback: Any = None,
    ) -> np.ndarray:
        self.recorded_count += 1
        if self._fake_audio is not None:
            audio = self._fake_audio
        else:
            # 2.5 seconds of simulated clean speech at -12 dBFS
            t = np.arange(int(samplerate * 2.5)) / samplerate
            # 1s room tone, 0.5s tone, 1s room tone
            audio = np.zeros(len(t), dtype=np.float32)
            speech_idx = int(samplerate * 1.0)
            speech_end = int(samplerate * 1.5)
            # -12 dBFS tone = 10^(-12/20) ~ 0.251
            audio[speech_idx:speech_end] = 0.25 * np.sin(2.0 * np.pi * 440.0 * t[:speech_end - speech_idx])
            # add tiny room noise (-45 dBFS)
            audio += (np.random.rand(len(t)).astype(np.float32) - 0.5) * 0.005

        if meter_callback:
            meter_callback(audio[:1000])
        return audio

    def play(self, audio: np.ndarray, samplerate: int = 48000) -> None:
        self.played_count += 1


# ── Audio Analysis & 24-bit Packing Helpers ──────────────────────────────────

def compute_metrics(audio: np.ndarray, samplerate: int = 48000) -> dict[str, Any]:
    duration = len(audio) / float(samplerate) if samplerate > 0 else 0.0
    if len(audio) == 0:
        return {
            "duration": 0.0,
            "peak": 0.0,
            "peak_dBFS": -999.0,
            "is_clipped": False,
            "lead_rms_dBFS": -999.0,
            "trail_rms_dBFS": -999.0,
        }

    peak = float(np.max(np.abs(audio)))
    peak_dBFS = float(20.0 * math.log10(peak)) if peak > 0 else -999.0
    is_clipped = peak >= 0.999

    # Room tone lead & trail (first 0.5s and last 0.5s)
    half_sec = int(samplerate * 0.5)
    lead = audio[:half_sec] if len(audio) >= half_sec else audio
    trail = audio[-half_sec:] if len(audio) >= half_sec else audio

    lead_rms = float(np.sqrt(np.mean(lead**2))) if len(lead) > 0 else 0.0
    trail_rms = float(np.sqrt(np.mean(trail**2))) if len(trail) > 0 else 0.0

    lead_dBFS = float(20.0 * math.log10(lead_rms)) if lead_rms > 0 else -999.0
    trail_dBFS = float(20.0 * math.log10(trail_rms)) if trail_rms > 0 else -999.0

    return {
        "duration": duration,
        "peak": peak,
        "peak_dBFS": peak_dBFS,
        "is_clipped": is_clipped,
        "lead_rms_dBFS": lead_dBFS,
        "trail_rms_dBFS": trail_dBFS,
    }


def write_wav_24bit(path: Path, audio: np.ndarray, samplerate: int = 48000) -> None:
    """Pack float numpy array in [-1.0, 1.0] into 24-bit PCM mono WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Clamp and scale to 24-bit signed integer [-8388608, 8388607]
    samples_int = np.clip(np.round(audio * 8388607.0), -8388608, 8388607).astype("<i4")
    # Take first 3 bytes (little-endian) of each 4-byte int32
    raw_3bytes = np.frombuffer(samples_int.tobytes(), dtype=np.uint8).reshape(-1, 4)[:, :3].tobytes()

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)      # mono
        wf.setsampwidth(3)      # 3 bytes = 24-bit
        wf.setframerate(samplerate)
        wf.writeframes(raw_3bytes)


def log_quality_flag(
    flags_path: Path,
    filename: str,
    reason: str,
    metrics: dict[str, Any],
) -> None:
    flags_path.parent.mkdir(parents=True, exist_ok=True)
    flags: list[dict[str, Any]] = []
    if flags_path.exists():
        try:
            with open(flags_path, "r", encoding="utf-8") as f:
                flags = json.load(f)
        except Exception:
            flags = []

    flags.append({
        "filename": filename,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "metrics": metrics,
    })

    with open(flags_path, "w", encoding="utf-8") as f:
        json.dump(flags, f, indent=2)


# ── Meter Formatter ──────────────────────────────────────────────────────────

def render_meter(peak_val: float) -> str:
    peak_db = 20.0 * math.log10(peak_val) if peak_val > 1e-5 else -60.0
    # Map -40 to 0 dBFS into 20 blocks
    norm = max(0.0, min(1.0, (peak_db + 40.0) / 40.0))
    bars = int(norm * 20)
    meter_str = "=" * bars + " " * (20 - bars)
    return f"[{meter_str}] {peak_db:5.1f} dBFS"


# ── Interactive Session Engine ───────────────────────────────────────────────

def run_session(
    manifest_path: Path,
    masters_dir: Path,
    quality_flags_path: Path,
    env_filter: str | None = None,
    sections_filter: list[str] | None = None,
    device: int | str | None = None,
    overwrite: bool = False,
    backend: AudioBackend | None = None,
    input_prompter: Any = None,
) -> int:
    if backend is None:
        backend = SoundDeviceBackend()

    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}", file=sys.stderr)
        return 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    clips: list[dict[str, Any]] = manifest.get("clips", [])

    # Order blocks: Q (C, E, I, G, A), then D, then N
    env_blocks = [
        ("Q", ["C", "E", "I", "G", "A"]),
        ("D", ["C", "E", "A"]),
        ("N", ["C", "E", "G", "A"]),
    ]

    ordered_clips: list[dict[str, Any]] = []
    for env_code, sec_order in env_blocks:
        env_clips = [c for c in clips if c.get("env") == env_code]
        for sec in sec_order:
            sc = [c for c in env_clips if c.get("section") == sec]
            sc.sort(key=lambda c: (c.get("id", ""), c.get("take", 1)))
            ordered_clips.extend(sc)
        remaining = [c for c in env_clips if c.get("section") not in sec_order]
        remaining.sort(key=lambda c: (c.get("section", ""), c.get("id", ""), c.get("take", 1)))
        ordered_clips.extend(remaining)

    # Apply filters
    if env_filter:
        ordered_clips = [c for c in ordered_clips if c.get("env") == env_filter.upper()]
    if sections_filter:
        sec_set = {s.upper() for s in sections_filter}
        ordered_clips = [c for c in ordered_clips if c.get("section") in sec_set]

    # Find missing clips
    masters_dir.mkdir(parents=True, exist_ok=True)
    existing_files = {p.name for p in masters_dir.glob("*.wav")}

    pending_clips: list[dict[str, Any]] = []
    for c in ordered_clips:
        fname = c.get("filename", "")
        if overwrite or fname not in existing_files:
            pending_clips.append(c)

    print("\n=== DAIMON CORPUS RECORDER CLI ===")
    print(f"Total matching clips:  {len(ordered_clips)}")
    print(f"Already recorded:      {len(ordered_clips) - len(pending_clips)}")
    print(f"Pending to record:     {len(pending_clips)}")
    print(f"Master output dir:     {masters_dir}")
    print(f"Format:                48000 Hz, Mono, 24-bit PCM WAV")

    if not pending_clips:
        print("\nAll selected clips have already been recorded! (Pass --overwrite to re-record).")
        return 0

    prompt_fn = input_prompter or input

    for idx, clip in enumerate(pending_clips, 1):
        fname = clip["filename"]
        target_wav = masters_dir / fname
        text = clip.get("text", "")
        delivery_note = clip.get("condition", "natural pace, ~1s silence before/after")
        sec = clip.get("section", "")
        env = clip.get("env", "")
        take = clip.get("take", 1)

        while True:
            print("\n" + "=" * 70)
            print(f"Clip [{idx}/{len(pending_clips)}] : {fname}")
            print(f"Section {sec} [{env}] | Take {take}")
            print(f"Text to say  : \"{text}\"")
            print(f"Delivery Note: {delivery_note}")
            print("=" * 70)

            # Wait for Enter to begin
            p_val = prompt_fn("Press [Enter] to START recording (or 's' to skip, 'q' to quit): ")
            if p_val.strip().lower() == "q":
                print("Session aborted by user.")
                return 0
            if p_val.strip().lower() == "s":
                print(f"Skipped {fname}.")
                break

            print("\nRECORDING... Speak naturally with ~1s room tone at start and end.")
            print("Press [Enter] to STOP recording.")

            # Record
            def meter_cb(chunk: np.ndarray) -> None:
                peak = float(np.max(np.abs(chunk))) if len(chunk) > 0 else 0.0
                meter = render_meter(peak)
                sys.stdout.write(f"\r  LIVE LEVEL: {meter}   ")
                sys.stdout.flush()

            audio = backend.record(
                stop_event=None,
                samplerate=48000,
                device=device,
                meter_callback=meter_cb,
            )
            print()

            # Analyze recorded audio
            metrics = compute_metrics(audio, 48000)
            dur = metrics["duration"]
            peak_db = metrics["peak_dBFS"]
            clipped = metrics["is_clipped"]
            lead_db = metrics["lead_rms_dBFS"]
            trail_db = metrics["trail_rms_dBFS"]

            print(f"\n--- Take Analysis ---")
            print(f"Duration     : {dur:.2f} s")
            print(f"Peak dBFS    : {peak_db:.1f} dBFS")
            print(f"Lead silence : {lead_db:.1f} dBFS")
            print(f"Trail silence: {trail_db:.1f} dBFS")

            # Quality checks
            fault_note = ""
            if clipped:
                print(f"\n  [ERROR] CLIPPING DETECTED! Peak reached 0 dBFS.")
                fault_note = "clipping"
            elif peak_db < -18.0:
                print(f"\n  [WARN] Level too quiet (Peak {peak_db:.1f} dBFS < -18 dBFS).")
            elif peak_db > -3.0:
                print(f"\n  [WARN] Level close to clipping (Peak {peak_db:.1f} dBFS > -3 dBFS).")

            # Post-take menu
            action_prompt = (
                "\nActions: [Enter] Accept & save | [r] Redo take | [p] Playback | [s] Skip | [q] Quit\n"
                "Choice: "
            )
            action = prompt_fn(action_prompt).strip().lower()

            while action == "p":
                print(f"Playing back {fname}...")
                backend.play(audio, 48000)
                action = prompt_fn(action_prompt).strip().lower()

            if action == "q":
                print("Session aborted by user.")
                return 0
            elif action == "s":
                print(f"Skipped {fname}.")
                break
            elif action == "r":
                reason = fault_note or prompt_fn("Reason for retake (clipping / noise / wrong line / other): ").strip()
                log_quality_flag(quality_flags_path, fname, reason, metrics)
                print(f"Logged retake reason '{reason}' to {quality_flags_path.name}. Retaking...")
                continue
            else:
                # Accept and write 24-bit PCM master WAV
                write_wav_24bit(target_wav, audio, 48000)
                print(f"SAVED: {target_wav} (48 kHz mono 24-bit)")
                break

    print(f"\nAll requested clips processed! Master files saved in {masters_dir}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Daimon Corpus Recorder CLI.")
    parser.add_argument("--list-devices", action="store_true", help="List audio input devices and exit")
    parser.add_argument("--device", help="Audio input device index or substring name")
    parser.add_argument("--env", choices=["Q", "D", "N"], help="Filter by environment (Q, D, N)")
    parser.add_argument("--sections", nargs="+", help="Filter by sections (e.g. C E I G A)")
    parser.add_argument("--manifest", default=str(REPO_ROOT / "evals" / "corpus" / "manifest.json"))
    parser.add_argument("--masters-dir", default=str(REPO_ROOT / "evals" / "corpus" / "masters"))
    parser.add_argument("--quality-flags", default=str(REPO_ROOT / "evals" / "corpus" / "quality_flags.json"))
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing clips")

    args = parser.parse_args()

    backend = SoundDeviceBackend()

    if args.list_devices:
        devices = backend.list_devices()
        print("\n=== Available Audio Input Devices ===")
        for d in devices:
            print(f"  [{d['index']}] {d['name']} (Channels: {d['max_input_channels']}, Default Rate: {d['default_samplerate']} Hz)")
        return 0

    return run_session(
        manifest_path=Path(args.manifest),
        masters_dir=Path(args.masters_dir),
        quality_flags_path=Path(args.quality_flags),
        env_filter=args.env,
        sections_filter=args.sections,
        device=int(args.device) if args.device and args.device.isdigit() else args.device,
        overwrite=args.overwrite,
        backend=backend,
    )


if __name__ == "__main__":
    sys.exit(main())
