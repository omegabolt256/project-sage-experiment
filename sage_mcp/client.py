from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters, stdio_client


SERVER_ROOT = Path(r"D:\Sage\sage_mcp\servers")

SERVER_FILES = {
    "filesystem": SERVER_ROOT / "filesystem.py",
    "git": SERVER_ROOT / "git.py",
}


class MCPClient:
    def __init__(self, server: str = "filesystem"):
        if server not in SERVER_FILES:
            raise ValueError(
                f"Unknown MCP server: {server}. "
                f"Available servers: {sorted(SERVER_FILES)}"
            )

        self.server = server
        self.server_file = SERVER_FILES[server]

    async def list_tools(self):
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_file)],
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
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

    async def call_tool(self, name: str, arguments: dict):
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_file)],
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
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
