# Sage Warden Memory Benchmark

Target:
- Windows laptop
- ~8 GB physical RAM
- CPU-only Warden test

## Integrated single-process result

| Component | Integrated RSS delta |
|---|---:|
| Python baseline | 21.5 MB |
| Silero VAD | +39.6 MB |
| Wake-word runtime proxy | +156.5 MB |
| Streaming ASR | +133.2 MB |
| Piper TTS | +68.2 MB |
| **Combined Warden RSS** | **419.1 MB** |

## Important comparison

Earlier isolated-process measurements were approximately:

- VAD: +39.4 MB
- Wake word: +192.6 MB
- Streaming ASR: +139.1 MB
- Piper: +116.1 MB

A naive sum produced approximately 508.6 MB, while the actual combined
single-process result was approximately 419.1 MB.

This demonstrates why the integrated benchmark is the meaningful measurement.

## ASR experiment

The Indian-English streaming Zipformer was approximately +133.2 MB in the
integrated Warden test, but conversational testing showed poor recognition
for the intended multilingual/Hinglish use case.

The experiment therefore separated:
- streaming/low-memory suitability
from
- language suitability.

The model was useful as a benchmark, but was not accepted as the final Sage
Hinglish ASR.
