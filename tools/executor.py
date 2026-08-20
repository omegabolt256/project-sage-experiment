from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.registry import ToolRegistry


@dataclass
class ToolExecutor:
    registry: ToolRegistry

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        return self.registry.execute(name, **arguments)
