import numpy as np
import sounddevice as sd
import sherpa_onnx
from pathlib import Path

D = Path(r"D:\Sage\tools\audio\sherpa-onnx\indian-en")
RATE = 16000
CHUNK = 1600

r = sherpa_onnx.OnlineRecognizer.from_transducer(
    tokens=str(D / "tokens.txt"),
    encoder=str(D / "encoder.onnx"),
    decoder=str(D / "decoder.onnx"),
    joiner=str(D / "joiner.onnx"),
    num_threads=1,
    sample_rate=RATE,
    feature_dim=80,
    decoding_method="greedy_search",
    enable_endpoint_detection=True,
    rule1_min_trailing_silence=0.8,
    rule2_min_trailing_silence=0.8,
    rule3_min_utterance_length=20.0,
)

s = r.create_stream()

print("Speak now...")

with sd.InputStream(
    samplerate=RATE,
    channels=1,
    dtype="float32",
    blocksize=CHUNK,
) as mic:

    while True:
        audio, overflow = mic.read(CHUNK)

        if overflow:
            print("audio overflow")

        audio = np.asarray(audio[:, 0], dtype=np.float32)

        s.accept_waveform(RATE, audio)

        while r.is_ready(s):
            r.decode_stream(s)

        text = r.get_result(s).strip()

        if text:
            print("\r" + text, end="", flush=True)

        if r.is_endpoint(s):
            break

final = r.get_result(s).strip()

print()
print("FINAL:", final)
