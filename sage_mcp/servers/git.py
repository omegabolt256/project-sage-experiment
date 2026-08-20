from __future__ import annotations

import subprocess
from pathlib import Path

from mcp.server import MCPServer


WORKSPACE = Path(r"D:\Sage").resolve()

server = MCPServer("sage-git")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or f"Git command failed with exit code {result.returncode}."
        )

    return result.stdout.strip()


@server.tool()
def git_status() -> str:
    """Show the current Git status."""
    return _git("status", "--short", "--branch")


@server.tool()
def git_log(limit: int = 10) -> str:
    """Show recent Git commits."""
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100.")

    return _git(
        "log",
        f"-{limit}",
        "--oneline",
        "--decorate",
    )


@server.tool()
def git_diff() -> str:
    """Show unstaged Git changes."""
    return _git("diff")


@server.tool()
def git_add(path: str = ".") -> str:
    """Stage a file or directory inside the Sage workspace."""

    requested = (WORKSPACE / path).resolve()

    try:
        requested.relative_to(WORKSPACE)
    except ValueError as exc:
        raise ValueError(
            "Git path must remain inside the Sage workspace."
        ) from exc

    relative = requested.relative_to(WORKSPACE)

    return _git(
        "add",
        "--",
        str(relative),
    )


@server.tool()
def git_commit(message: str) -> str:
    """Create a Git commit."""

    if not message.strip():
        raise ValueError("Commit message cannot be empty.")

    return _git(
        "commit",
        "-m",
        message,
    )


@server.tool()
def git_push() -> str:
    """Push commits to the configured Git remote."""
    return _git("push")


if __name__ == "__main__":
    server.run("stdio")
