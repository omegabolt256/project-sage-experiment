from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sage_mcp.client import call_tool


def _result(response: Any) -> Any:
    """Extract the useful result from an MCP CallToolResult."""
    structured = getattr(response, "structured_content", None)

    if isinstance(structured, dict) and "result" in structured:
        return structured["result"]

    content = getattr(response, "content", None)

    if content:
        text = getattr(content[0], "text", None)
        if isinstance(text, str):
            return text

    return response


@dataclass
class MemoryBridge:
    """Sage memory backend backed by MemPalace MCP."""

    wing: str = "user"
    room: str = "general"

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> Any:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")

        response = call_tool(
            "mempalace_search",
            {
                "query": query.strip(),
                "limit": limit,
                "wing": self.wing,
            },
            server="mempalace",
        )

        return _result(response)

    def remember(self, content: str) -> str:
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must be a non-empty string.")

        content = content.strip()

        duplicate = _result(
            call_tool(
                "mempalace_check_duplicate",
                {
                    "content": content,
                    "threshold": 0.9,
                },
                server="mempalace",
            )
        )

        if isinstance(duplicate, dict):
            if duplicate.get("duplicate") is True:
                return content

        response = call_tool(
            "mempalace_add_drawer",
            {
                "wing": self.wing,
                "room": self.room,
                "content": content,
                "added_by": "sage",
            },
            server="mempalace",
        )

        result = _result(response)

        if isinstance(result, dict):
            stored = result.get("content")
            if isinstance(stored, str):
                return stored

        return content

    def update(
        self,
        drawer_id: str,
        content: str,
    ) -> str:
        if not isinstance(drawer_id, str) or not drawer_id.strip():
            raise ValueError("drawer_id must be a non-empty string.")

        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must be a non-empty string.")

        response = call_tool(
            "mempalace_update_drawer",
            {
                "drawer_id": drawer_id,
                "content": content.strip(),
            },
            server="mempalace",
        )

        result = _result(response)

        if isinstance(result, dict):
            updated = result.get("content")
            if isinstance(updated, str):
                return updated

        return content.strip()

    def forget(self, drawer_id: str) -> Any:
        if not isinstance(drawer_id, str) or not drawer_id.strip():
            raise ValueError("drawer_id must be a non-empty string.")

        return _result(
            call_tool(
                "mempalace_delete_drawer",
                {"drawer_id": drawer_id},
                server="mempalace",
            )
        )

    def get(self) -> str:
        """Backward-compatible memory read.

        Returns a compact concatenation of the most relevant user memories.
        """
        results = self.search(
            "user preferences facts important personal information",
            limit=10,
        )

        if isinstance(results, list):
            parts: list[str] = []

            for item in results:
                if not isinstance(item, dict):
                    continue

                content = item.get("text") or item.get("content")

                if isinstance(content, str) and content.strip():
                    parts.append(content.strip())

            return "\n".join(parts)

        return ""

    def update_legacy(self, memory: str) -> str:
        """Compatibility helper: save the supplied memory as a new drawer."""
        return self.remember(memory)


if __name__ == "__main__":
    bridge = MemoryBridge()

    print("=== MemPalace memory ===")
    print(bridge.get())
