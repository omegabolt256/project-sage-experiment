# Sage Benchmarks

## Target machine

These measurements were made during the Sage experiment on the target Windows laptop.

- OS: Windows
- RAM class: ~8 GB
- CPU-only Warden
- Python-based orchestrator
- 16 kHz mono audio for ASR tests

The numbers below are experiment-specific.

---

## Warden — integrated single-process RSS

| Stage | Increment | Cumulative RSS |
|---|---:|---:|
| Baseline | 21.5 MB | 21.5 MB |
| Silero VAD | +39.6 MB | 61.1 MB |
| Wake-word runtime proxy | +156.5 MB | 217.6 MB |
| Streaming ASR | +133.2 MB | 350.8 MB |
| Piper TTS | +68.2 MB | 419.1 MB |

**Final measured Warden RSS: 419.1 MB**

Soft ceiling: **500 MB**

Hard ceiling: **750 MB**

Headroom below soft ceiling: **80.9 MB**

---

## Warden — standalone process measurements

| Component | Standalone delta |
|---|---:|
| VAD | 39.4 MB |
| Wake word | 192.6 MB |
| Streaming ASR | 139.1 MB |
| Piper | 116.1 MB |

Naive separate-process sum including baseline:

**≈508.6 MB**

Integrated process:

**419.1 MB**

Difference:

**≈89.5 MB**

Interpretation: runtime libraries, allocator behavior, and shared process state mean the naive sum is not the correct deployment budget.

---

## Piper

Measured standalone process delta:

**116.1 MB**

Measured integrated Warden delta:

**68.2 MB**

The difference reinforced the need to benchmark the real integrated process.

---

## Streaming ASR candidate

The first Warden streaming candidate was the Indian-English Zipformer.

Integrated memory contribution:

**+133.2 MB**

The model passed the streaming/footprint test but failed the intended language-quality requirement for multilingual/Hinglish interaction.

This was a useful negative result.

---

## Qwen3-ASR Worker experiment

Successful local OpenASR run:

- Model: Qwen3-ASR 0.6B q4
- Audio: 10 s
- CPU backend
- Inference time: ≈4.38 s
- RTF: ≈0.439x
- Admitted model memory: ≈763 MB

This strongly supported keeping the stronger ASR model as a Worker instead of a resident Warden model.

---

## Benchmark principle

For local assistants:

> **Measure resident RSS after loading the exact integrated process. Do not infer it from model-file size.**

For streaming ASR:

> **Measure language quality and memory together. A model that fits but cannot handle the target speech pattern is not a successful candidate.**
