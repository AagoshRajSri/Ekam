import asyncio
import os
import wave
from pathlib import Path
from dotenv import load_dotenv
import pytest
from livekit.agents.utils import http_context
from livekit.plugins import groq

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

@pytest.mark.asyncio
async def test_pronunciation():
    # PowerShell command to run this test manually (no -o flag):
    #   $env:RUN_LIVE_TTS_TESTS=1; uv run --directory services/agent pytest tests/test_orpheus_pronunciation.py -v -s
    if not os.getenv("RUN_LIVE_TTS_TESTS"):
        pytest.skip("Skipping manual live TTS pronunciation test by default. Set RUN_LIVE_TTS_TESTS=1 to run.")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY not set")

    async with http_context.open():
        tts_engine = groq.TTS(
            model="canopylabs/orpheus-v1-english",
            voice="autumn",
            api_key=api_key,
        )

        out_dir = Path(__file__).resolve().parent / "tmp_audio"
        out_dir.mkdir(exist_ok=True)
        out_wav = out_dir / "daimon_orpheus.wav"

        print("Synthesizing 'Hello, I am Daimon' with Orpheus...")
        stream = tts_engine.synthesize("Hello, I am Daimon.")
        
        frames = []
        sample_rate = 24000
        num_channels = 1
        
        async for event in stream:
            if hasattr(event, "frame") and event.frame:
                frames.append(event.frame.data)
                sample_rate = event.frame.sample_rate
                num_channels = event.frame.num_channels

        raw_bytes = b"".join(frames)
        with wave.open(str(out_wav), "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2) # 16-bit PCM
            wf.setframerate(sample_rate)
            wf.writeframes(raw_bytes)

        print(f"Saved audio to {out_wav} ({len(raw_bytes)} bytes, {sample_rate} Hz)")

        # Now let's test transcribing it with Groq Whisper to check phonetics
        from livekit import rtc
        stt_engine = groq.STT(
            model="whisper-large-v3-turbo",
            language="en",
            api_key=api_key,
        )

        samples = len(raw_bytes) // (num_channels * 2)
        frame1 = rtc.AudioFrame(
            data=raw_bytes,
            sample_rate=sample_rate,
            num_channels=num_channels,
            samples_per_channel=samples,
        )
        res1 = await stt_engine.recognize(buffer=frame1)
        print("Whisper transcription of 'Daimon':", [a.text for a in res1.alternatives])

        # Also test synthesizing respelling "Daymon"
        out_wav_respell = out_dir / "daymon_orpheus.wav"
        print("Synthesizing 'Hello, I am Daymon' with Orpheus...")
        stream2 = tts_engine.synthesize("Hello, I am Daymon.")
        frames2 = []
        async for event in stream2:
            if hasattr(event, "frame") and event.frame:
                frames2.append(event.frame.data)
        
        raw_bytes2 = b"".join(frames2)
        with wave.open(str(out_wav_respell), "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(raw_bytes2)
        print(f"Saved respelled audio to {out_wav_respell}")

        samples2 = len(raw_bytes2) // (num_channels * 2)
        frame2 = rtc.AudioFrame(
            data=raw_bytes2,
            sample_rate=sample_rate,
            num_channels=num_channels,
            samples_per_channel=samples2,
        )
        res2 = await stt_engine.recognize(buffer=frame2)
        print("Whisper transcription of 'Daymon':", [a.text for a in res2.alternatives])

if __name__ == "__main__":
    asyncio.run(test_pronunciation())
