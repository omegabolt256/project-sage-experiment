from __future__ import annotations

from typing import Any

from core.evidence_store import EvidenceStore
from core.task_state import TaskState
from core.task_store import TaskStore


class TaskManager:
    def __init__(
        self,
        store: TaskStore | None = None,
        evidence: EvidenceStore | None = None,
    ) -> None:
        self.store = store or TaskStore()
        self.evidence = evidence or EvidenceStore()
        self._active: dict[str, TaskState] = {}

    def current(self, conversation_id: str) -> TaskState | None:
        if conversation_id in self._active:
            return self._active[conversation_id]

        saved = self.store.load(conversation_id)
        if saved is None:
            return None

        state = TaskState(
            task_id=saved["task_id"],
            intent=saved["intent"],
            topic=saved["topic"],
            active_capability=saved["active_capability"],
            current_focus=saved["current_focus"],
            depth=saved["depth"],
        )
        state.tool_results = saved.get("tool_results", [])
        self._active[conversation_id] = state
        return state

    def start(
        self,
        conversation_id: str,
        intent: str,
        topic: str = "",
        capability: str = "",
    ) -> TaskState:
        state = TaskState(
            intent=intent,
            topic=topic,
            active_capability=capability,
        )
        self._active[conversation_id] = state
        self.store.save(conversation_id, state)
        return state

    def ensure(
        self,
        conversation_id: str,
        intent: str = "",
        topic: str = "",
        capability: str = "",
    ) -> TaskState:
        state = self.current(conversation_id)

        if state is None:
            return self.start(
                conversation_id,
                intent,
                topic,
                capability,
            )

        if intent:
            state.intent = intent
        if topic:
            state.topic = topic
        if capability:
            state.active_capability = capability

        self.store.save(conversation_id, state)
        return state

    def record_tool_result(
        self,
        conversation_id: str,
        tool: str,
        arguments: dict[str, Any],
        result: Any,
    ) -> None:
        state = self.ensure(conversation_id)
        state.add_tool_result(tool, arguments, result)

        # Keep only compact task metadata in tasks.db.
        self.store.save(conversation_id, state)

    def set_focus(
        self,
        conversation_id: str,
        focus: str,
        depth: str | None = None,
    ) -> None:
        state = self.ensure(conversation_id)
        state.current_focus = focus
        if depth:
            state.depth = depth
        self.store.save(conversation_id, state)
