from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    tools: tuple[str, ...] = field(default_factory=tuple)


class CapabilityRouter:
    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        if capability.name in self._capabilities:
            raise ValueError(
                f"Capability already registered: {capability.name}"
            )

        self._capabilities[capability.name] = capability

    def get(self, name: str) -> Capability:
        try:
            return self._capabilities[name]
        except KeyError as exc:
            raise ValueError(
                f"Unknown capability: {name}"
            ) from exc

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": capability.name,
                "description": capability.description,
                "tools": list(capability.tools),
            }
            for capability in self._capabilities.values()
        ]

    def find_for_tool(self, tool_name: str) -> Capability | None:
        for capability in self._capabilities.values():
            if tool_name in capability.tools:
                return capability

        return None
