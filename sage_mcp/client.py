import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters, stdio_client


SERVER_FILE = Path(r"D:\Sage\sage_mcp\servers\filesystem.py")


class MCPClient:
    def __init__(self, server_file: Path = SERVER_FILE):
        self.server_file = server_file

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


def list_tools():
    return asyncio.run(MCPClient().list_tools())


def call_tool(name: str, arguments: dict):
    return asyncio.run(
        MCPClient().call_tool(name, arguments)
    )
