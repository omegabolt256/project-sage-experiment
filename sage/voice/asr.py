from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import sounddevice as sd
import sherpa_onnx

from sage.events.voice_event import EventType, event_bus


ASR_DIR = Path(
    os.getenv(
        "SAGE_ASR_MODEL_DIR",
        r"D:\Sage\tools\audio\sherpa-onnx\indian-en",
    )
)

SAMPLE_RATE = 16000
CHUNK_MS = 100


class SherpaASR:
    def __init__(self):
        required = [
            ASR_DIR / "tokens.txt",
            ASR_DIR / "encoder.onnx",
            ASR_DIR / "decoder.onnx",
            ASR_DIR / "joiner.onnx",
        ]

        missing = [str(p) for p in required if not p.is_file()]
        if missing:
            raise FileNotFoundError(
                "Missing Sherpa ASR files:\n  - "
                + "\n  - ".join(missing)
            )

        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(ASR_DIR / "tokens.txt"),
            encoder=str(ASR_DIR / "encoder.onnx"),
            decoder=str(ASR_DIR / "decoder.onnx"),
            joiner=str(ASR_DIR / "joiner.onnx"),
            num_threads=1,
            sample_rate=SAMPLE_RATE,
            feature_dim=80,
            decoding_method="greedy_search",
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=0.8,
            rule2_min_trailing_silence=0.8,
            rule3_min_utterance_length=20.0,
            provider="cpu",
        )

        self.stream = None

    def start_utterance(self):
        self.stream = self.recognizer.create_stream()

    def feed(self, samples: np.ndarray) -> tuple[str, bool]:
        if self.stream is None:
            self.start_utterance()

        samples = np.asarray(samples, dtype=np.float32).reshape(-1)

        self.stream.accept_waveform(SAMPLE_RATE, samples)

        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)

        text = self.recognizer.get_result(self.stream).strip()
        endpoint = self.recognizer.is_endpoint(self.stream)

        if text:
            event_bus.emit(
                EventType.TRANSCRIPT_PARTIAL,
                {"text": text},
            )

        if endpoint:
            final_text = text

            # Reset for the next utterance.
            self.recognizer.reset(self.stream)
            self.stream = self.recognizer.create_stream()

            if final_text:
                event_bus.emit(
                    EventType.TRANSCRIPT_FINAL,
                    {
                        "text": final_text,
                        "source": "sherpa",
                    },
                )

            return final_text, True

        return text, False

    def finish(self) -> str:
        if self.stream is None:
            return ""

        tail = np.zeros(
            int(SAMPLE_RATE * 0.3),
            dtype=np.float32,
        )

        self.stream.accept_waveform(
            SAMPLE_RATE,
            tail,
        )
        self.stream.input_finished()

        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)

        text = self.recognizer.get_result(self.stream).strip()

        self.recognizer.reset(self.stream)
        self.stream = self.recognizer.create_stream()

        if text:
            event_bus.emit(
                EventType.TRANSCRIPT_FINAL,
                {
                    "text": text,
                    "source": "sherpa",
                },
            )

        return text


class MicrophoneASR:
    def __init__(self, asr: SherpaASR):
        self.asr = asr
        self.running = False
        self.stream = None

    def listen_once(self):
        self.running = True
        self.asr.start_utterance()

        samples_per_chunk = int(
            SAMPLE_RATE * CHUNK_MS / 1000
        )

        print("[Sage] Microphone active.")

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=samples_per_chunk,
            ) as self.stream:

                while self.running:
                    samples, overflowed = self.stream.read(
                        samples_per_chunk
                    )

                    if overflowed:
                        print(
                            "[Sage] Audio input overflow."
                        )

                    samples = samples.reshape(-1)

                    _, endpoint = self.asr.feed(samples)

                    if endpoint:
                        break

        finally:
            self.running = False
            self.stream = None

    def stop(self):
        self.running = False
