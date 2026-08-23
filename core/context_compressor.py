from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_URL_RE = re.compile(r"https?://\S+")
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)


@dataclass(frozen=True)
class CompressionBudget:
    max_context_chars: int = 14000
    max_tool_chars: int = 12000
    max_message_chars: int = 3000
    max_history_messages: int = 6
    max_evidence_items: int = 10
    max_evidence_chars: int = 12000


class ContextCompressor:
    """Deterministic context reduction for small/local models."""

    def __init__(self, budget: CompressionBudget | None = None) -> None:
        self.budget = budget or CompressionBudget()

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", str(text)).strip()

    @staticmethod
    def _preserve_identifiers(text: str) -> list[str]:
        return _URL_RE.findall(text) + _DOI_RE.findall(text)

    def _trim_preserving_identifiers(
        self,
        text: str,
        limit: int,
    ) -> str:
        text = str(text)

        if len(text) <= limit:
            return text

        identifiers = self._preserve_identifiers(text)

        head = max(0, limit // 2)
        tail = max(0, limit - head - 120)

        result = (
            text[:head]
            + "\n...[CONTEXT COMPRESSED]...\n"
            + text[-tail:]
        )

        for identifier in identifiers:
            if identifier not in result:
                remaining = limit - len(result) - len(identifier) - 2
                if remaining <= 0:
                    break
                result += f"\n{identifier}"

        return result[:limit]

    def compress_messages(
        self,
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        if not messages:
            return []

        recent = messages[-self.budget.max_history_messages :]

        compressed: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for message in recent:
            role = str(message.get("role", "user"))
            content = self._trim_preserving_identifiers(
                str(message.get("content", "")),
                self.budget.max_message_chars,
            )

            key = (role, self._normalize(content).lower())

            if key in seen:
                continue

            seen.add(key)
            compressed.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return compressed

    def compress_evidence(
        self,
        evidence: list[dict[str, Any]],
    ) -> str:
        if not evidence:
            return ""

        selected = evidence[: self.budget.max_evidence_items]
        blocks: list[str] = []

        for index, item in enumerate(selected, 1):
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            content = str(
                item.get("content")
                or item.get("snippet")
                or item.get("abstract")
                or ""
            ).strip()

            block = (
                f"[SOURCE {index}]\n"
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Content: {content}\n"
                f"[END SOURCE {index}]"
            )

            blocks.append(
                self._trim_preserving_identifiers(
                    block,
                    max(1200, self.budget.max_evidence_chars // max(1, len(selected))),
                )
            )

        return self._trim_preserving_identifiers(
            "\n\n".join(blocks),
            self.budget.max_evidence_chars,
        )

    def compress_tool_result(self, result: Any) -> str:
        return self._trim_preserving_identifiers(
            str(result),
            self.budget.max_tool_chars,
        )

    def compress_context_message(self, text: str) -> str:
        return self._trim_preserving_identifiers(
            text,
            self.budget.max_context_chars,
        )
