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
        provider="groq",
        model="openai/gpt-oss-20b",
    ),
    "reasoning": WorkloadRoute(
        provider="groq",
        model="openai/gpt-oss-20b",
    ),
    "agentic": WorkloadRoute(
        provider="groq",
        model="groq/compound",
    ),
    "coding": WorkloadRoute(
        provider="groq",
        model="openai/gpt-oss-20b",
    ),
    "private": WorkloadRoute(
        provider="ollama",
        model="qwen3:1.7b",
    ),
    "background": WorkloadRoute(
        provider="ollama",
        model="qwen3:1.7b",
    ),
}


def get_route(workload: str) -> WorkloadRoute:
    try:
        return ROUTES[workload]
    except KeyError as exc:
        raise ValueError(f"Unknown workload: {workload}") from exc
