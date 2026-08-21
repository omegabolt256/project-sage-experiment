from __future__ import annotations

import re

from memory.bridge import MemoryBridge


class MemoryManager:
    def __init__(self, bridge: MemoryBridge | None = None) -> None:
        self.bridge = bridge or MemoryBridge()

    def should_remember(self, message: str) -> bool:
        patterns = [
            r"\bremember this\b",
            r"\bremember that\b",
            r"\bplease remember\b",
            r"\bsave this\b",
            r"\bkeep this in mind\b",
            r"\bdon't forget\b",
        ]

        return any(
            re.search(pattern, message, re.IGNORECASE)
            for pattern in patterns
        )

    def extract_memory(self, message: str) -> str:
        cleaned = re.sub(
            r"(?i)^(please\s+)?remember\s+(this|that)\s*:?\s*",
            "",
            message.strip(),
        )

        cleaned = re.sub(
            r"(?i)^remember\s*:?\s*",
            "",
            cleaned,
        )

        return cleaned.strip()

    def remember(self, message: str) -> str:
        memory = self.extract_memory(message)

        if not memory:
            raise ValueError("No memory content detected.")

        return self.bridge.remember(memory)

    def recall(
        self,
        query: str,
        limit: int = 5,
    ):
        return self.bridge.search(query, limit=limit)
