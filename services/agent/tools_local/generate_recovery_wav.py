"""
Generate recovery_429.wav using local Piper TTS model.
Zero external API calls.
Target: 24 kHz mono 16-bit PCM WAV.
Wording: "I've hit my voice limit, switching to my backup voice."
"""

import audioop
import wave
from pathlib import Path
from piper.voice import PiperVoice

AGENT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = AGENT_DIR / "models" / "piper" / "en_US-lessac-medium.onnx"
CONFIG_PATH = AGENT_DIR / "models" / "piper" / "en_US-lessac-medium.onnx.json"
OUT_WAV = AGENT_DIR / "assets" / "recovery_429.wav"

TEXT = "I've hit my voice limit, switching to my backup voice."


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Piper model not found at {MODEL_PATH}")

    print(f"Loading Piper model from {MODEL_PATH}...")
    voice = PiperVoice.load(
        model_path=str(MODEL_PATH),
        config_path=str(CONFIG_PATH) if CONFIG_PATH.exists() else None,
    )

    in_rate = voice.config.sample_rate  # usually 22050
    out_rate = 24000
    print(f"Synthesizing: '{TEXT}' (model rate: {in_rate} Hz, target rate: {out_rate} Hz)...")

    raw_chunks = []
    for chunk in voice.synthesize(TEXT):
        raw_chunks.append(chunk.audio_int16_bytes)

    raw_bytes = b"".join(raw_chunks)
    print(f"Raw audio synthesized: {len(raw_bytes)} bytes at {in_rate} Hz")

    # Resample to 24000 Hz
    if in_rate != out_rate:
        raw_bytes, _ = audioop.ratecv(raw_bytes, 2, 1, in_rate, out_rate, None)
        print(f"Resampled to {out_rate} Hz: {len(raw_bytes)} bytes")

    OUT_WAV.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT_WAV), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(out_rate)
        wf.writeframes(raw_bytes)

    duration = (len(raw_bytes) // 2) / out_rate
    print(f"Saved {OUT_WAV}: {len(raw_bytes)} bytes, {out_rate} Hz, mono 16-bit, {duration:.2f}s")


if __name__ == "__main__":
    main()
