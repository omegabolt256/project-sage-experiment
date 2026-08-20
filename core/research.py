from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.evidence_store import EvidenceStore
from tools.web import web_search
from tools.web_tools import fetch_web


@dataclass
class ResearchEngine:
    evidence: EvidenceStore

    def search(
        self,
        conversation_id: str,
        query: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        results = web_search(query, max_results)

        for item in results:
            if not isinstance(item, dict):
                continue
            self.evidence.add(
                conversation_id=conversation_id,
                source_type="web_search",
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                content=str(item.get("snippet", "")),
                metadata={"query": query},
            )

        return results

    def fetch(
        self,
        conversation_id: str,
        url: str,
        stealth: bool = False,
    ) -> dict[str, Any]:
        result = fetch_web(url, stealth)

        self.evidence.add(
            conversation_id=conversation_id,
            source_type="web_page",
            title=str(result.get("title", "")),
            url=str(result.get("url", url)),
            content=str(result.get("text", "")),
            metadata={"status": result.get("status"), "stealth": stealth},
        )

        return result

    def evidence_context(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> str:
        items = self.evidence.list_for_conversation(
            conversation_id,
            limit=limit,
        )

        if not items:
            return ""

        chunks: list[str] = []
        for index, item in enumerate(items, start=1):
            chunks.append(
                f"[SOURCE {index}]\n"
                f"Type: {item['source_type']}\n"
                f"Title: {item['title']}\n"
                f"URL: {item['url']}\n"
                f"Content:\n{item['content']}\n"
                f"[END SOURCE {index}]"
            )

        return "\n\n".join(chunks)
