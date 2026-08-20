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


def create_capability_router() -> CapabilityRouter:
    router = CapabilityRouter()

    router.register(
        Capability(
            name="research",
            description=(
                "Find, retrieve, inspect, compare, and synthesize "
                "information from the web and scholarly sources."
            ),
            tools=(
                "web_search",
                "web_fetch",
                "paper_search",
                "paper_bibtex",
            ),
        )
    )

    router.register(
        Capability(
            name="memory",
            description=(
                "Read and update persistent information about the user."
            ),
            tools=("remember",),
        )
    )

    router.register(
        Capability(
            name="calculation",
            description="Perform deterministic arithmetic.",
            tools=("calculator",),
        )
    )

    router.register(
        Capability(
            name="browser",
            description=(
                "Interact with websites through deterministic browser automation."
            ),
            tools=(
                "browser_open",
            ),
        )
    )

    router.register(
        Capability(
            name="document",
            description=(
                "Convert documents into structured evidence using Docling."
            ),
            tools=("docling_ingest",),
        )
    )

    router.register(
        Capability(
            name="conversation",
            description=(
                "Answer questions, reason about information, "
                "and maintain conversational context."
            ),
            tools=(),
        )
    )

    router.register(
        Capability(
            name="filesystem",
            description=(
                "Read, write, search, and inspect files within "
                "the controlled Sage workspace through MCP."
            ),
            tools=(
                "list_files",
                "read_file",
                "write_file",
                "search_files",
            ),
        )
    )

    return router


