from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.tools import Tool


WORKSPACE = Path(r"D:\Sage\workspace").resolve()


def safe_path(relative_path: str) -> Path:
    """Resolve a path while preventing access outside the Sage workspace."""
    candidate = (WORKSPACE / relative_path).resolve()

    if candidate != WORKSPACE and WORKSPACE not in candidate.parents:
        raise PermissionError(
            "Access outside D:\\Sage\\workspace is not allowed."
        )

    return candidate


def list_files(path: str = ".") -> list[str]:
    """List files and directories inside the Sage workspace."""
    target = safe_path(path)

    if not target.exists():
        raise FileNotFoundError(path)

    if not target.is_dir():
        raise NotADirectoryError(path)

    return [
        str(item.relative_to(WORKSPACE))
        for item in sorted(target.iterdir())
    ]


def read_file(path: str) -> str:
    """Read a UTF-8 text file from the Sage workspace."""
    target = safe_path(path)

    if not target.exists():
        raise FileNotFoundError(path)

    if not target.is_file():
        raise IsADirectoryError(path)

    return target.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    """Write a UTF-8 text file inside the Sage workspace."""
    target = safe_path(path)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    return f"Written: {target.relative_to(WORKSPACE)}"


def search_files(query: str, path: str = ".") -> list[str]:
    """Search UTF-8 text files inside the Sage workspace."""
    target = safe_path(path)

    if not target.exists():
        raise FileNotFoundError(path)

    results = []

    for file in target.rglob("*"):
        if not file.is_file():
            continue

        try:
            text = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        if query.lower() in text.lower():
            results.append(str(file.relative_to(WORKSPACE)))

    return results


mcp_tools = [
    Tool.from_function(list_files),
    Tool.from_function(read_file),
    Tool.from_function(write_file),
    Tool.from_function(search_files),
]


server = MCPServer(
    name="sage-filesystem",
    description="Controlled filesystem access for Sage.",
    version="1.0.0",
    tools=mcp_tools,
)


if __name__ == "__main__":
    server.run("stdio")
