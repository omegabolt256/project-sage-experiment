from pathlib import Path
import tempfile

from sage.protocol.types import OperationKind
from sage.storage.artifact_store import ArtifactStore
from sage.storage.context_store import ContextStore
from sage.storage.operation_log import OperationLog

root = Path(tempfile.mkdtemp(prefix="sage-storage-test-"))

# ContextStore remains healthy.
ctx = ContextStore(root / "context")
ctx.put("context://task/1/status", {"status": "pending"})
ctx.put("context://task/1/status", {"status": "done"})
assert ctx.get("context://task/1/status").value["status"] == "done"

# ArtifactStore hashes and publishes atomically.
source = root / "sample.bin"
source.write_bytes(b"SAGE ARTIFACT TEST")
artifacts = ArtifactStore(root / "artifacts")
ref = artifacts.put_file("artifact://tests/sample.bin", source)
assert ref.path.read_bytes() == b"SAGE ARTIFACT TEST"
assert artifacts.get("artifact://tests/sample.bin").sha256 == ref.sha256

# OperationLog persists and reconstructs operations.
log = OperationLog(root / "operations.sqlite3")
op = log.create(
    node_id="desktop-01",
    kind=OperationKind.ADD,
    target="reminder://milk",
    payload={"text": "buy milk"},
)
assert log.get(op.id) == op
ops = list(log.iter_target("reminder://milk"))
assert len(ops) == 1
assert ops[0].vector_clock.counters["desktop-01"] == 1
log.close()

print("SAGE SHARED SEMANTICS STORAGE OK")
print("ContextStore: OK")
print("ArtifactStore: OK")
print("OperationLog: OK")