import os
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import sherpa_onnx

from piper import PiperVoice
from sage.events.voice_event import EventType, event_bus
from sage.storage.context_store import ContextStore
from sage.voice.keyboard_wake import KeyboardWake


SAGE = Path(r"D:\Sage")

ASR = SAGE / "tools" / "audio" / "sherpa-onnx" / "indian-en"
TTS = SAGE / "tools" / "audio" / "piper" / "voices" / "en_US-lessac-medium.onnx"

RATE = 16000
CHUNK = 1600


class Sage:
    def __init__(self):
        self.context = ContextStore(SAGE / "data" / "context")
        self.wake = KeyboardWake("f8")

        self.asr = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(ASR / "tokens.txt"),
            encoder=str(ASR / "encoder.onnx"),
            decoder=str(ASR / "decoder.onnx"),
            joiner=str(ASR / "joiner.onnx"),
            num_threads=1,
            sample_rate=RATE,
            feature_dim=80,
            decoding_method="greedy_search",
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=0.8,
            rule2_min_trailing_silence=0.8,
            rule3_min_utterance_length=20.0,
        )

        self.voice = PiperVoice.load(str(TTS))
        self.speaking = False
        self.listening = False

        event_bus.on(EventType.WAKE_DETECTED, self.listen)

    def listen(self, _):
        if self.listening or self.speaking:
            return

        self.listening = True
        print("[Sage] Listening...")

        stream = self.asr.create_stream()

        try:
            with sd.InputStream(
                samplerate=RATE,
                channels=1,
                dtype="float32",
                blocksize=CHUNK,
            ) as mic:

                while True:
                    audio, overflow = mic.read(CHUNK)

                    if overflow:
                        print("[Sage] audio overflow")

                    audio = np.asarray(
                        audio[:, 0],
                        dtype=np.float32,
                    )

                    stream.accept_waveform(
                        RATE,
                        audio,
                    )

                    while self.asr.is_ready(stream):
                        self.asr.decode_stream(stream)

                    text = self.asr.get_result(stream).strip()

                    if self.asr.is_endpoint(stream):
                        break

            text = self.asr.get_result(stream).strip()

            if not text:
                print("[Sage] Nothing heard.")
                return

            print(f"[User] {text}")

            self.context.put(
                "context://conversation/last_user",
                text,
            )

            reply = f"I heard you say: {text}"

            self.context.put(
                "context://conversation/last_sage",
                reply,
            )

            self.speak(reply)

        except Exception as e:
            print(f"[Sage ERROR] {e}")

        finally:
            self.listening = False

    def speak(self, text):
        self.speaking = True
        print(f"[Sage] {text}")

        try:
            audio = []

            for chunk in self.voice.synthesize(text):
                audio.append(
                    np.asarray(
                        chunk.audio_float_array,
                        dtype=np.float32,
                    )
                )

            if audio:
                audio = np.concatenate(audio)

                sd.play(
                    audio,
                    samplerate=22050,
                )
                sd.wait()

        except Exception as e:
            print(f"[Sage TTS ERROR] {e}")

        finally:
            self.speaking = False

    def run(self):
        print("[Sage] Ready.")
        print("[Sage] Press F8, then speak.")
        print("[Sage] Ctrl+C to quit.")

        self.wake.start()

        try:
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            pass

        finally:
            self.wake.stop()


if __name__ == "__main__":
    Sage().run()
