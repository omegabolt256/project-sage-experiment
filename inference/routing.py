from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Provider = Literal["groq", "ollama"]


@dataclass(frozen=True)
class WorkloadRoute:
    provider: Provider
    model: str


ROUTES: dict[str, WorkloadRoute] = {
    "chat": WorkloadRoute(
        provider="ollama",
        model="qwen2.5:3b",
    ),
    "reasoning": WorkloadRoute(
        provider="ollama",
        model="qwen2.5:3b",
    ),
    "agentic": WorkloadRoute(
        provider="ollama",
        model="qwen2.5:3b",
    ),
    "coding": WorkloadRoute(
        provider="ollama",
        model="qwen2.5:3b",
    ),
    "private": WorkloadRoute(
        provider="ollama",
        model="qwen2.5:3b",
    ),
    "background": WorkloadRoute(
        provider="ollama",
        model="qwen2.5:3b",
    ),
}


def get_route(workload: str) -> WorkloadRoute:
    try:
        return ROUTES[workload]
    except KeyError as exc:
        raise ValueError(f"Unknown workload: {workload}") from exc

