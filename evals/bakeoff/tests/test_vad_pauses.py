import asyncio
import json
import wave
from pathlib import Path
import numpy as np
from livekit.plugins import silero
from livekit import rtc


async def evaluate_sentence_splitting():
    vad = silero.VAD.load(
        min_speech_duration=0.05,
        min_silence_duration=0.5,
        activation_threshold=0.4,
        sample_rate=16000,
        force_cpu=True,
    )

    corpus_dir = Path("evals/corpus/wavs")
    gt = json.load(open("evals/corpus/ground_truth.json"))

    test_clips = [
        "s01_Q_cmd_01_t1.wav",
        "s01_Q_cmd_02_t1.wav",
        "s01_Q_cmd_03_t1.wav",
        "s01_Q_cmd_04_t1.wav",
        "s01_Q_cmd_05_t1.wav",
        "s01_Q_cmd_06_t1.wav",
        "s01_Q_cmd_07_t1.wav",
        "s01_Q_cmd_08_t1.wav",
        "s01_Q_cmd_09_t1.wav",
        "s01_Q_cmd_10_t1.wav",
    ]

    results = []
    frame_size = 320  # 20ms at 16kHz

    for clip in test_clips:
        wav_path = corpus_dir / clip
        with wave.open(str(wav_path), "rb") as wf:
            n_frames = wf.getnframes()
            data = wf.readframes(n_frames)
            samples = np.frombuffer(data, dtype=np.int16)

        stream = vad.stream()
        total_chunks = len(samples) // frame_size
        events = []

        async def read_events():
            async for ev in stream:
                events.append((ev.type.name, round(ev.timestamp, 3) if hasattr(ev, "timestamp") else None))

        read_task = asyncio.create_task(read_events())

        for i in range(total_chunks):
            chunk = samples[i * frame_size : (i + 1) * frame_size]
            frame = rtc.AudioFrame(
                data=chunk.tobytes(),
                sample_rate=16000,
                num_channels=1,
                samples_per_channel=frame_size,
            )
            stream.push_frame(frame)
            await asyncio.sleep(0.001)

        stream.end_input()
        await stream.aclose()
        await read_task

        start_events = [e for e in events if e[0] == "START_OF_SPEECH"]
        end_events = [e for e in events if e[0] == "END_OF_SPEECH"]
        is_split = len(start_events) > 1

        results.append({
            "clip": clip,
            "text": gt.get(clip, {}).get("text", ""),
            "speech_starts": len(start_events),
            "speech_ends": len(end_events),
            "is_split": is_split,
        })

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(evaluate_sentence_splitting())
