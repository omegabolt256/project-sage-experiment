"""
sage_warden_ram_probe.py

Incremental RSS measurement harness for the Sage warden stack.
Implements the 11-step plan: baseline, then load each warden component
one at a time, printing the RSS delta and running total after each.

Usage:
    python sage_warden_ram_probe.py                # run every stage
    python sage_warden_ram_probe.py --stage vad     # just one stage
    python sage_warden_ram_probe.py --stage wakeword
    python sage_warden_ram_probe.py --stage streamingasr
    python sage_warden_ram_probe.py --stage tts

Env vars (point these at your actual model files before running):
    SAGE_VAD_MODEL        path to silero_vad.onnx
    SAGE_WAKEWORD_MODEL   path to your wake word model
    SAGE_ASR_MODEL_DIR    directory with tokens.txt / encoder.onnx /
                           decoder.onnx / joiner.onnx (sherpa-onnx layout)
    SAGE_TTS_MODEL        path to a piper .onnx voice

Install only what you're testing this run:
    pip install psutil onnxruntime          # baseline + VAD
    pip install sherpa-onnx                 # streaming ASR candidate A
    pip install piper-tts                   # TTS
    pip install openwakeword                # wake word

To A/B whisper.cpp tiny against sherpa-onnx, swap the body of
load_streaming_asr() below and rerun — compare the printed deltas
directly, same machine, same run structure.
"""

import argparse
import gc
import os
import sys
import time

try:
    import psutil
except ImportError:
    sys.exit("Install psutil first: pip install psutil --break-system-packages")

PROCESS = psutil.Process(os.getpid())


def rss_mb() -> float:
    """Current resident set size in MB, after a settle + gc pass."""
    gc.collect()
    time.sleep(0.2)  # let the OS reclaim freed pages before sampling
    return PROCESS.memory_info().rss / (1024 * 1024)


def _single_thread_opts():
    import onnxruntime as ort
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    opts.inter_op_num_threads = 1
    return opts


# ---- Stage loaders ---------------------------------------------------
# Each returns the loaded object so it stays referenced (not GC'd) for
# the rest of the run -- that's what makes the RSS delta meaningful.

def load_vad():
    import onnxruntime as ort
    model_path = os.environ.get("SAGE_VAD_MODEL", r"C:\Users\shaik\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\silero_vad\data\silero_vad_16k_op15.onnx")
    return ort.InferenceSession(
        model_path,
        sess_options=_single_thread_opts(),
        providers=["CPUExecutionProvider"],
    )


def load_wakeword():
    from openwakeword.model import Model
    model_path = os.environ.get("SAGE_WAKEWORD_MODEL")
    kwargs = {"wakeword_models": [model_path]} if model_path else {}
    return Model(**kwargs)


def load_streaming_asr():
    # A/B point #1: sherpa-onnx (shown) vs whisper.cpp tiny.
    import sherpa_onnx
    model_dir = os.environ.get("SAGE_ASR_MODEL_DIR", r"D:\Sage\tools\audio\sherpa-onnx\indian-en")
    return sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=f"{model_dir}/tokens.txt",
        encoder=f"{model_dir}/encoder.onnx",
        decoder=f"{model_dir}/decoder.onnx",
        joiner=f"{model_dir}/joiner.onnx",
        num_threads=1,
        sample_rate=16000,
        feature_dim=80,
    )


def load_tts():
    # A/B point #2: swap voice path to compare Piper medium vs low quality.
    from piper import PiperVoice
    voice_path = os.environ.get("SAGE_TTS_MODEL", r"D:\Sage\tools\audio\piper\voices\en_US-lessac-medium.onnx")
    return PiperVoice.load(voice_path)


STAGES = [
    ("VAD", load_vad),
    ("Wake word", load_wakeword),
    ("Streaming ASR", load_streaming_asr),
    ("Piper TTS", load_tts),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=["all"] + [name.lower().replace(" ", "") for name, _ in STAGES],
        default="all",
    )
    args = parser.parse_args()

    keep_alive = []
    baseline = rss_mb()
    print(f"{'Baseline (interpreter + deps)':<32} {baseline:8.1f} MB\n")

    for name, loader in STAGES:
        key = name.lower().replace(" ", "")
        if args.stage != "all" and args.stage != key:
            continue
        before = rss_mb()
        try:
            keep_alive.append(loader())
        except Exception as e:
            print(f"{name:<32} SKIPPED  ({type(e).__name__}: {e})")
            continue
        after = rss_mb()
        print(f"{name:<32} +{after - before:6.1f} MB   "
              f"(cumulative +{after - baseline:6.1f} MB, total {after:7.1f} MB)")

    total = rss_mb()
    print(f"\n{'TOTAL warden RSS':<32} {total:8.1f} MB "
          f"(+{total - baseline:.1f} MB over interpreter baseline)")


if __name__ == "__main__":
    main()

