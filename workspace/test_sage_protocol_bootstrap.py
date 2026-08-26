from pathlib import Path
import tempfile

from sage.protocol.types import (
    Capability, CapabilityCatalog, CapabilityStatus, CapabilityTier,
    Operation, OperationKind, VectorClock,
)
from sage.storage.context_store import ContextStore

root = Path(tempfile.mkdtemp(prefix="sage-context-test-"))
store = ContextStore(root / "context")

v1 = store.put("context://task/123/status", {"status": "pending"})
v2 = store.put("context://task/123/status", {"status": "running"})
assert v1 != v2

result = store.get("context://task/123/status")
assert result.version == v2
assert result.value["status"] == "running"

clock = VectorClock({"desktop-01": 1})
next_clock = clock.increment("desktop-01")
assert next_clock.counters["desktop-01"] == 2

cap = Capability(
    name="calculator",
    description="Fast arithmetic",
    tier=CapabilityTier.PREFECT,
    version="1",
)
catalog = CapabilityCatalog(
    node_id="desktop-01",
    capabilities=(cap,),
    heartbeat_at_ms=0,
    heartbeat_ttl_ms=15000,
)
assert catalog.get("calculator").name == "calculator"
assert OperationKind.UPDATE.value == "update"

print("SAGE PROTOCOL BOOTSTRAP OK")
print("ContextStore atomic/versioned smoke test: OK")
print("CapabilityCatalog smoke test: OK")
print("VectorClock smoke test: OK")