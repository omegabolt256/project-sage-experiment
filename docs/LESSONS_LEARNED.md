# Lessons Learned

## 1. Measure the integrated process

The biggest quantitative lesson was the difference between separate-process estimates and the actual integrated RSS.

Naive sum:
≈508.6 MB

Actual integrated Warden:
≈419.1 MB

Design from the real process, not the sum.

## 2. Model size is not RAM size

Small ONNX files can still create large runtime footprints because execution providers, allocators, preprocessing, and framework state contribute heavily to RSS.

## 3. Streaming is necessary but not sufficient

The Indian-English streaming Zipformer demonstrated a good memory/latency profile but failed the intended multilingual/Hinglish quality requirement.

The correct candidate must satisfy:

```text
streaming
+ language coverage
+ code-switching quality
+ acceptable RSS
+ CPU latency
```

## 4. Resident components are special

VAD, wake, ASR, and TTS are needed on essentially every conversational turn, so loading them on demand undermines voice continuity and barge-in.

## 5. Heavy models belong in Workers

Qwen3-ASR q4 required roughly 763 MB of admitted runtime memory during the successful local run.

That is a poor Warden resident candidate for an 8 GB machine but a reasonable Worker-level capability.

## 6. Avoid premature distributed infrastructure

The local-first ContextStore, ArtifactStore, and OperationLog provided a useful abstraction without requiring Redis, Qdrant, Celery, or Kubernetes.

The local system should work before the distributed system exists.

## 7. Keep voice events separate from tools

The voice layer should generate events such as:

```text
wake_detected
transcript_partial
transcript_final
interrupt
tts_start
tts_end
```

The Warden decides what those events mean.

## 8. Prototype the painful thing first

Voice was correctly identified as the most difficult non-fakeable part of the assistant.

A text-only prototype can hide audio boundary, latency, barge-in, and ASR quality problems.

---

# What would be done differently

If the project were restarted:

1. Define the target speech mix before choosing the Warden ASR.
2. Benchmark multilingual streaming ASR candidates head-to-head before writing voice orchestration code.
3. Keep the integrated RSS probe from day one.
4. Build the Warden voice event interface before adding tools.
5. Treat the Desktop/Mobile/Cloud axis as a deployment concern, not part of the local MVP.
