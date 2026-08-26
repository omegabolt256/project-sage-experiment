from sage.events.voice_event import EventType, VoiceEventBus
from sage.storage.context_store import ContextStore

from pathlib import Path
import tempfile

bus = VoiceEventBus()
seen = []

bus.on(
    EventType.WAKE_DETECTED,
    lambda data: seen.append(data),
)

bus.emit(
    EventType.WAKE_DETECTED,
    {"source": "test"},
)

assert seen == [{"source": "test"}]

root = Path(
    tempfile.mkdtemp(prefix="sage-day1-")
)

store = ContextStore(root)

version = store.put(
    "context://conversation/test",
    "hello",
)

result = store.get(
    "context://conversation/test"
)

assert result.version == version
assert result.value == "hello"

print("SAGE DAY-1 VOICE SKELETON OK")
print("VoiceEventBus: OK")
print("ContextStore integration: OK")
