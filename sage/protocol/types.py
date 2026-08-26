from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

class CapabilityTier(StrEnum):
    WARDEN = "warden"
    PREFECT = "prefect"
    WORKER = "worker"
    GRASS = "grass"

class CapabilityStatus(StrEnum):
    AVAILABLE = "available"
    BUSY = "busy"
    DEGRADED = "degraded"
    OFFLINE = "offline"

class OperationKind(StrEnum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    APPEND = "append"

@dataclass(frozen=True, slots=True)
class VectorClock:
    counters: Mapping[str, int] = field(default_factory=dict)

    def increment(self, node_id: str) -> "VectorClock":
        c = dict(self.counters)
        c[node_id] = c.get(node_id, 0) + 1
        return VectorClock(c)

    def dominates(self, other: "VectorClock") -> bool:
        keys = set(self.counters) | set(other.counters)
        greater = False
        for k in keys:
            a = self.counters.get(k, 0)
            b = other.counters.get(k, 0)
            if a < b:
                return False
            if a > b:
                greater = True
        return greater

    def concurrent_with(self, other: "VectorClock") -> bool:
        return (
            self != other
            and not self.dominates(other)
            and not other.dominates(self)
        )

@dataclass(frozen=True, slots=True)
class Operation:
    id: str
    kind: OperationKind
    target: str
    payload: Mapping[str, Any]
    timestamp_ms: int
    node_id: str
    vector_clock: VectorClock

@dataclass(frozen=True, slots=True)
class Capability:
    name: str
    description: str
    tier: CapabilityTier
    version: str
    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    requires: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    estimated_ram_mb: int | None = None
    privacy_class: str = "local"
    supports_streaming: bool = False

@dataclass(frozen=True, slots=True)
class CapabilityCatalog:
    node_id: str
    capabilities: tuple[Capability, ...]
    heartbeat_at_ms: int
    heartbeat_ttl_ms: int = 15_000
    generation: int = 0

    def get(self, name: str) -> Capability | None:
        return next((c for c in self.capabilities if c.name == name), None)

    def is_stale(self, now_ms: int) -> bool:
        return now_ms - self.heartbeat_at_ms > self.heartbeat_ttl_ms