from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPServer:
    name: str
    description: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class MCPRegistry:
    def __init__(self):
        self._servers: dict[str, MCPServer] = {}

    def register(self, server: MCPServer) -> MCPServer:
        self._servers[server.name] = server
        return server

    def get(self, name: str) -> MCPServer:
        if name not in self._servers:
            raise KeyError(f"MCP server not registered: {name}")
        return self._servers[name]

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": server.name,
                "description": server.description,
                "transport": server.transport,
                "command": server.command,
                "args": server.args,
                "enabled": server.enabled,
            }
            for server in self._servers.values()
        ]

    def enable(self, name: str):
        self.get(name).enabled = True

    def disable(self, name: str):
        self.get(name).enabled = False


def create_mcp_registry() -> MCPRegistry:
    registry = MCPRegistry()

    registry.register(
        MCPServer(
            name="filesystem",
            description="Controlled access to Sage workspace files.",
            metadata={
                "allowed_roots": [
                    r"D:\Sage\workspace",
                ]
            },
        )
    )

    registry.register(
        MCPServer(
            name="git",
            description="Git repository inspection and version-control operations.",
        )
    )

    registry.register(
        MCPServer(
            name="sqlite",
            description="Controlled access to Sage SQLite databases.",
            metadata={
                "allowed_databases": [
                    r"D:\Sage\data\tasks.db",
                    r"D:\Sage\data\evidence.db",
                ]
            },
        )
    )

    return registry
