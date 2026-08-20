from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ToolParameter:
    name: str
    description: str
    type: str
    required: bool = True


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    parameters: list[ToolParameter] = field(default_factory=list)

    def schema(self) -> dict[str, Any]:
        properties = {}

        for parameter in self.parameters:
            properties[parameter.name] = {
                "type": parameter.type,
                "description": parameter.description,
            }

        required = [
            parameter.name
            for parameter in self.parameters
            if parameter.required
        ]

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ValueError(f"Unknown tool: {name}") from exc

    def list(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def execute(self, name: str, **kwargs: Any) -> Any:
        tool = self.get(name)

        allowed = {
            parameter.name
            for parameter in tool.parameters
        }

        unknown = set(kwargs) - allowed

        if unknown:
            raise ValueError(
                f"Tool '{name}' received unknown arguments: "
                f"{sorted(unknown)}"
            )

        missing = [
            parameter.name
            for parameter in tool.parameters
            if parameter.required and parameter.name not in kwargs
        ]

        if missing:
            raise ValueError(
                f"Tool '{name}' is missing required arguments: {missing}"
            )

        return tool.handler(**kwargs)
