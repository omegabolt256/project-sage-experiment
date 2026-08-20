from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class Evidence:
    source_type: str
    title: str = ""
    url: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskState:
    task_id: str = field(default_factory=lambda: str(uuid4()))
    intent: str = ""
    topic: str = ""
    active_capability: str = ""
    current_focus: str = ""
    depth: str = "overview"

    sources: list[Evidence] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)

    def add_evidence(self, evidence: Evidence) -> None:
        self.sources.append(evidence)

    def add_tool_result(
        self,
        tool: str,
        arguments: dict[str, Any],
        result: Any,
    ) -> None:
        self.tool_results.append(
            {
                "tool": tool,
                "arguments": arguments,
                "result": result,
            }
        )

    def summary(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "intent": self.intent,
            "topic": self.topic,
            "active_capability": self.active_capability,
            "current_focus": self.current_focus,
            "depth": self.depth,
            "source_count": len(self.sources),
            "tool_result_count": len(self.tool_results),
        }
