from __future__ import annotations

from collections import defaultdict, deque
from enum import StrEnum
from threading import RLock


class EventType(StrEnum):
    WAKE_DETECTED = "wake_detected"
    SPEECH_START = "speech_start"
    TRANSCRIPT_PARTIAL = "transcript_partial"
    TRANSCRIPT_FINAL = "transcript_final"
    RESPONSE_READY = "response_ready"
    TTS_START = "tts_start"
    TTS_END = "tts_end"
    INTERRUPT = "interrupt"
    ERROR = "error"


class VoiceEventBus:
    def __init__(self, history_size: int = 500):
        self._listeners = defaultdict(list)
        self._history = deque(maxlen=history_size)
        self._lock = RLock()

    def on(self, event_type, callback):
        with self._lock:
            self._listeners[event_type].append(callback)

    def emit(self, event_type, data=None):
        with self._lock:
            self._history.append({
                "type": event_type.value,
                "data": data,
            })
            listeners = tuple(self._listeners.get(event_type, ()))

        for callback in listeners:
            try:
                callback(data)
            except Exception as exc:
                print(f"[Sage] Event handler error: {exc}")

    def history(self):
        with self._lock:
            return list(self._history)


event_bus = VoiceEventBus()
