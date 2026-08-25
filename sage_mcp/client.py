from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client, httpx2


SERVER_ROOT = Path(r"D:\Sage\sage_mcp\servers")

SERVER_FILES = {
    "filesystem": SERVER_ROOT / "filesystem.py",
    "git": SERVER_ROOT / "git.py",
    "sqlite": SERVER_ROOT / "sqlite.py",
}

EXTERNAL_SERVERS = {
    "mempalace": {
        "command": "mempalace-mcp",
        "args": [
            "--palace",
            os.getenv(
                "SAGE_MEMPALACE_PATH",
                r"D:\Sage\memory\mempalace",
            ),
        ],
    },
    "paperfind": {
        "command": "paper-find-mcp",
        "args": [],
    },
    "wigolo": {
        "command": "npx",
        "args": ["wigolo"],
    },
}

HTTP_SERVERS = {
    "x64dbg": {
        "url": "http://127.0.0.1:9094",
        "token_env": "SAGE_X64DBG_TOKEN",
    },
}


class MCPClient:
    def __init__(self, server: str = "filesystem") -> None:
        available = (
            set(SERVER_FILES)
            | set(EXTERNAL_SERVERS)
            | set(HTTP_SERVERS)
        )

        if server not in available:
            raise ValueError(
                f"Unknown MCP server: {server}. "
                f"Available servers: {sorted(available)}"
            )

        self.server = server
        self.server_file = SERVER_FILES.get(server)

        external = EXTERNAL_SERVERS.get(server)
        self.external_command = None
        self.external_args: list[str] = []

        if isinstance(external, dict):
            self.external_command = external["command"]
            self.external_args = external.get("args", [])

        self.http_config = HTTP_SERVERS.get(server)

    def _http_headers(self) -> dict[str, str]:
        if not self.http_config:
            return {}

        token_env = self.http_config.get("token_env")
        token = os.getenv(token_env, "").strip() if token_env else ""

        if not token:
            raise RuntimeError(
                f"{token_env} is not configured for MCP server "
                f"'{self.server}'."
            )

        return {
            "Authorization": f"Bearer {token}",
        }

    async def list_tools(self):
        if self.http_config:
            headers = self._http_headers()

            async with httpx2.AsyncClient(
                headers=headers,
                timeout=120.0,
            ) as http_client:
                async with streamable_http_client(
                    self.http_config["url"],
                    http_client=http_client,
                ) as streams:
                    read_stream, write_stream = streams

                    async with ClientSession(
                        read_stream,
                        write_stream,
                    ) as session:
                        await session.initialize()
                        result = await session.list_tools()

                        return [
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "input_schema": tool.input_schema,
                            }
                            for tool in result.tools
                        ]

        if self.external_command:
            server_params = StdioServerParameters(
                command=self.external_command,
                args=self.external_args,
            )
        else:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[str(self.server_file)],
            )

        async with stdio_client(server_params) as streams:
            read_stream, write_stream = streams

            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:
                await session.initialize()
                result = await session.list_tools()

                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                    }
                    for tool in result.tools
                ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ):
        if self.http_config:
            headers = self._http_headers()

            async with httpx2.AsyncClient(
                headers=headers,
                timeout=120.0,
            ) as http_client:
                async with streamable_http_client(
                    self.http_config["url"],
                    http_client=http_client,
                ) as streams:
                    read_stream, write_stream = streams

                    async with ClientSession(
                        read_stream,
                        write_stream,
                    ) as session:
                        await session.initialize()

                        return await session.call_tool(
                            name,
                            arguments=arguments,
                        )

        if self.external_command:
            server_params = StdioServerParameters(
                command=self.external_command,
                args=self.external_args,
            )
        else:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[str(self.server_file)],
            )

        async with stdio_client(server_params) as streams:
            read_stream, write_stream = streams

            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:
                await session.initialize()

                return await session.call_tool(
                    name,
                    arguments=arguments,
                )


def list_tools(server: str = "filesystem"):
    return asyncio.run(
        MCPClient(server).list_tools()
    )


def call_tool(
    name: str,
    arguments: dict,
    server: str = "filesystem",
):
    return asyncio.run(
        MCPClient(server).call_tool(
            name,
            arguments,
        )
    )
