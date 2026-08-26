# Project Sage — Experiment Archive

Project Sage was an experimental attempt to build a lightweight, voice-first
personal assistant for modest Windows hardware.

The project is archived as an engineering experiment rather than a finished
assistant.

## Key result

A single Python process containing the resident voice stack was measured at
approximately 419 MB RSS on the target 8 GB Windows laptop:

- Silero VAD: +39.6 MB
- Wake-word runtime proxy: +156.5 MB
- Streaming ASR: +133.2 MB
- Piper TTS: +68.2 MB
- Combined Warden RSS: ~419.1 MB

The measurements were taken with the components resident in the same process.
They are therefore more representative than simply summing separate-process
measurements.

## Architecture

The project explored two independent axes:

### Capability axis
- Warden
- Prefect
- Worker
- Grass

### Deployment axis
- Desktop Sage
- Mobile Sage
- Cloud Sage

The intent was to keep the conversational substrate resident while activating
heavy capabilities only when needed.

## Important findings

- Model file size is not the same as resident memory.
- Separate-process RSS measurements can differ substantially from combined
  single-process RSS.
- A streaming model optimized for Indian English was fast and memory-efficient
  but inadequate for Hindi/Hinglish conversational use.
- The audio pipeline and resource-management architecture should be measured on
  the target hardware rather than designed from model-file estimates.
- A lightweight local-first architecture can be practical on an 8 GB machine,
  but model selection is the limiting factor.

## Status

Archived. The repository preserves the implementation, experiments,
benchmarks, and architectural lessons learned during development.
