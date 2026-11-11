import wave, json
from pathlib import Path
import numpy as np
from livekit.plugins.silero.onnx_model import OnnxModel, new_inference_session


def evaluate_sentence_splitting():
    session = new_inference_session(force_cpu=True)
    model = OnnxModel(onnx_session=session, sample_rate=16000)

    gt = json.load(open("evals/corpus/ground_truth.json", "r", encoding="utf-8"))
    corpus_dir = Path("evals/corpus/wavs")

    # 10 confirmed DEV split clips from Section C
    dev_clips = [
        "s01_Q_cmd_03_t1.wav",
        "s01_Q_cmd_03_t2.wav",
        "s01_Q_cmd_04_t1.wav",
        "s01_Q_cmd_04_t2.wav",
        "s01_Q_cmd_05_t1.wav",
        "s01_Q_cmd_05_t2.wav",
        "s01_Q_cmd_06_t1.wav",
        "s01_Q_cmd_06_t2.wav",
        "s01_Q_cmd_07_t1.wav",
        "s01_Q_cmd_10_t1.wav",
    ]

    results = []

    for clip in dev_clips:
        wav_path = corpus_dir / clip
        with wave.open(str(wav_path), "rb") as wf:
            n_frames = wf.getnframes()
            data = wf.readframes(n_frames)
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

        model.reset()
        win_size = model.window_size_samples  # 512 samples = 32ms

        speaking = False
        speech_segments = 0
        silence_frames = 0
        silence_threshold = int(0.5 / (win_size / 16000))  # ~15.6 frames (0.5s pause)

        for i in range(len(samples) // win_size):
            chunk = samples[i * win_size : (i + 1) * win_size]
            prob = model(chunk)

            if prob > 0.40:
                if not speaking:
                    speaking = True
                    speech_segments += 1
                silence_frames = 0
            else:
                if speaking:
                    silence_frames += 1
                    if silence_frames >= silence_threshold:
                        speaking = False

        ref_text = gt.get(clip, {}).get("text", "")
        is_split = speech_segments > 1
        results.append({
            "clip": clip,
            "segments": speech_segments,
            "is_split": is_split,
            "text": ref_text,
        })

    return results


def test_vad_pause_evaluation():
    results = evaluate_sentence_splitting()
    assert len(results) == 10
    # Exactly 1 clip (cmd_10_t1 with 540ms internal breath pause) is split at 0.5s pause threshold
    split_count = sum(1 for r in results if r["is_split"])
    assert split_count == 1
    assert any(r["clip"] == "s01_Q_cmd_10_t1.wav" and r["is_split"] for r in results)


if __name__ == "__main__":
    res = evaluate_sentence_splitting()
    print(json.dumps(res, indent=2))
