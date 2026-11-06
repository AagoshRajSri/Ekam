import os
import sys
from pathlib import Path

# Ensure services/agent root is first on sys.path
AGENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT))

from dotenv import load_dotenv
import pytest
from livekit.plugins import silero, groq
import agent
from agent import Baby, prewarm, _SYSTEM_PROMPT


def test_environment_loads():
    env_path = Path(__file__).resolve().parents[3] / ".env"
    assert env_path.exists(), ".env file must exist"
    load_dotenv(env_path)
    assert os.getenv("GROQ_API_KEY"), "GROQ_API_KEY must be configured"
    assert os.getenv("LIVEKIT_URL"), "LIVEKIT_URL must be configured"
    assert os.getenv("LIVEKIT_API_KEY"), "LIVEKIT_API_KEY must be configured"
    assert os.getenv("LIVEKIT_API_SECRET"), "LIVEKIT_API_SECRET must be configured"


def test_agent_class_instantiation():
    agent = Baby()
    assert agent is not None
    assert "You are Baby" in _SYSTEM_PROMPT


def test_silero_vad_loads():
    vad = silero.VAD.load(
        min_speech_duration=0.05,
        min_silence_duration=0.55,
        activation_threshold=0.5,
        sample_rate=16000,
        force_cpu=True,
    )
    assert vad is not None


def test_groq_stt_instantiates():
    stt = groq.STT(
        model="whisper-large-v3-turbo",
        language="en",
        api_key=os.environ.get("GROQ_API_KEY", "dummy"),
    )
    assert stt is not None


def test_groq_llm_instantiates():
    llm = groq.LLM(
        model="qwen/qwen3.8-27b",
        api_key=os.environ.get("GROQ_API_KEY", "dummy"),
        temperature=0.4,
        max_completion_tokens=120,
    )
    assert llm is not None


def test_groq_tts_instantiates():
    tts = groq.TTS(
        model="canopylabs/orpheus-v1-english",
        voice="autumn",
        api_key=os.environ.get("GROQ_API_KEY", "dummy"),
    )
    assert tts is not None
