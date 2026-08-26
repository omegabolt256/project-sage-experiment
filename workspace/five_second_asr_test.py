import numpy as np
import sounddevice as sd
import sherpa_onnx
from pathlib import Path
import time

D = Path(r"D:\Sage\tools\audio\sherpa-onnx\indian-en")

RATE = 16000
CHUNK = 1600
SECONDS = 5

r = sherpa_onnx.OnlineRecognizer.from_transducer(
    tokens=str(D / "tokens.txt"),
    encoder=str(D / "encoder.onnx"),
    decoder=str(D / "decoder.onnx"),
    joiner=str(D / "joiner.onnx"),
    num_threads=1,
    sample_rate=RATE,
    feature_dim=80,
    decoding_method="greedy_search",
    enable_endpoint_detection=False,
    provider="cpu",
)

s = r.create_stream()

print("Speak for 5 seconds...")
print("Starting microphone NOW")

with sd.InputStream(
    samplerate=RATE,
    channels=1,
    dtype="float32",
    blocksize=CHUNK,
) as mic:

    start = time.perf_counter()

    while time.perf_counter() - start < SECONDS:
        audio, overflow = mic.read(CHUNK)

        if overflow:
            print("[audio overflow]")

        audio = np.asarray(
            audio[:, 0],
            dtype=np.float32,
        )

        s.accept_waveform(RATE, audio)

        while r.is_ready(s):
            r.decode_stream(s)

        text = r.get_result(s).strip()

        if text:
            print(f"\rASR: {text}", end="", flush=True)

# Force the stream to finish.
s.input_finished()

while r.is_ready(s):
    r.decode_stream(s)

final = r.get_result(s).strip()

print()
print()
print("FINAL:", final)
print("DONE")
