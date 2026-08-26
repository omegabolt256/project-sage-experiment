# Sage Architecture

## 1. Capability axis

```text
                    SAGE
                      │
                  WARDEN
                      │
                  PREFECT
                      │
                   WORKER
                      │
                    GRASS
```

### Warden
Permanent conversational substrate.

- audio capture
- VAD
- wake
- streaming ASR
- TTS
- conversation state
- router
- resource management

### Prefect
Lightweight capability that does not require heavy model activation.

### Worker
Heavy capability loaded/warmed only when needed.

### Grass
Rare specialist tooling.

---

## 2. Deployment axis

```text
                    SAGE IDENTITY
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
     Desktop            Mobile            Cloud
        │                 │                 │
     full node        lightweight        relay/
     capability       node              optional
     stack                              workers
```

The two axes are independent.

A capability is *what* Sage can do.
A node is *where* that capability may execute.

---

## 3. Shared semantics

The system was designed around four local-first abstractions:

```text
ContextStore
    structured state

ArtifactStore
    immutable artifacts

OperationLog
    durable operations

NodeRegistry
    live nodes and capabilities
```

These were kept transport-agnostic so they could later be backed by network services without forcing distributed infrastructure into the local prototype.

---

## 4. Routing

Routing belongs above Shared Semantics.

```text
Voice/Text Event
      │
      ▼
Sage Router
      │
      ├── intent
      ├── capability
      ├── node
      ├── memory pressure
      ├── latency
      ├── privacy
      └── warm/cold state
      │
      ▼
Capability / Node
```

---

## 5. Voice event architecture

```text
Microphone
    │
    ▼
VoiceEngine
    │
    ├── WAKE_DETECTED
    ├── SPEECH_START
    ├── TRANSCRIPT_PARTIAL
    ├── TRANSCRIPT_FINAL
    ├── TTS_START
    ├── TTS_END
    └── INTERRUPT
             │
             ▼
           Warden
```

The voice subsystem produces events; it does not directly orchestrate tools.

---

## 6. Memory policy

The resident Warden was given a 500 MB soft ceiling.

```text
GREEN
  ↓
YELLOW
  stop prefetch / reduce Worker TTL
  ↓
ORANGE
  unload idle Workers
  ↓
RED
  preserve Warden
  terminate non-essential Workers
```

The core invariant:

> **Never sacrifice the Warden to save memory.**

---

## 7. Distributed direction

The long-term design was:

```text
Desktop Sage ←→ Sage Protocol ←→ Mobile Sage
                      │
                      └────────── Cloud Sage
```

Each node keeps a partial local view of Shared Semantics and synchronizes operations when connectivity exists.

This was designed but not completed in the experiment.
