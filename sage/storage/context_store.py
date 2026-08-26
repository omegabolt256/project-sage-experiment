from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True, slots=True)
class VersionedValue:
    uri: str
    version: str
    value: Any
    created_at_ms: int

class ContextStore:
    """Local-first atomic/versioned storage for logical context:// URIs."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(uri: str) -> str:
        if not uri.startswith("context://"):
            raise ValueError("ContextStore requires context:// URI")
        key = uri[len("context://"):].strip("/")
        if not key or ".." in Path(key).parts:
            raise ValueError(f"Unsafe context URI: {uri}")
        return key

    @staticmethod
    def _version(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()[:20]

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        tmp_path = Path(tmp)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def put(self, uri: str, value: Any) -> str:
        key = self._key(uri)
        created = int(time.time() * 1000)
        payload = json.dumps(
            {"uri": uri, "created_at_ms": created, "value": value},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        version = self._version(payload)
        folder = self.root / key
        immutable = folder / f"{version}.json"
        latest = folder / "LATEST"

        if not immutable.exists():
            self._atomic_write(immutable, payload)
        self._atomic_write(latest, version.encode("ascii"))
        return version

    def get(self, uri: str) -> VersionedValue:
        folder = self.root / self._key(uri)
        latest = folder / "LATEST"
        if not latest.exists():
            raise KeyError(uri)

        version = latest.read_text(encoding="ascii").strip()
        immutable = folder / f"{version}.json"
        if not immutable.exists():
            raise RuntimeError(f"Context integrity error: {uri} -> {version}")

        doc = json.loads(immutable.read_text(encoding="utf-8"))
        return VersionedValue(uri, version, doc["value"], int(doc["created_at_ms"]))