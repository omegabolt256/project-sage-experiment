from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from core.evidence_store import EvidenceStore
from tools.web import web_search
from tools.web_tools import fetch_web


OPENALEX_API_URL = "https://api.openalex.org/works"


@dataclass
class ResearchEngine:
    evidence: EvidenceStore
    openalex_api_url: str = OPENALEX_API_URL
    timeout: float = 20.0

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

    def search_papers(
        self,
        conversation_id: str,
        query: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")

        if max_results < 1 or max_results > 50:
            raise ValueError("max_results must be between 1 and 50.")

        params: dict[str, Any] = {
            "search": query.strip(),
            "per-page": max_results,
        }

        api_key = os.getenv("OPENALEX_API_KEY", "").strip()

        if api_key:
            params["api_key"] = api_key

        response = httpx.get(
            self.openalex_api_url,
            params=params,
            timeout=self.timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": "Sage/1.0",
            },
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            raise RuntimeError("OpenAlex returned an invalid response.")

        raw_results = payload.get("results")

        if not isinstance(raw_results, list):
            raise RuntimeError("OpenAlex response is missing results.")

        papers: list[dict[str, Any]] = []

        for item in raw_results:
            if not isinstance(item, dict):
                continue

            paper = self._normalize_openalex_work(item)

            if not paper["title"]:
                continue

            papers.append(paper)

            self.evidence.add(
                conversation_id=conversation_id,
                source_type="academic_paper",
                title=paper["title"],
                url=paper["landing_page_url"] or paper["openalex_id"],
                content=self._paper_evidence_text(paper),
                metadata={
                    "provider": "openalex",
                    "query": query,
                    "openalex_id": paper["openalex_id"],
                    "doi": paper["doi"],
                    "publication_year": paper["year"],
                    "cited_by_count": paper["cited_by_count"],
                    "is_open_access": paper["is_open_access"],
                },
            )

        return papers

    def _normalize_openalex_work(
        self,
        item: dict[str, Any],
    ) -> dict[str, Any]:
        authors: list[str] = []

        raw_authorships = item.get("authorships")

        if isinstance(raw_authorships, list):
            for authorship in raw_authorships:
                if not isinstance(authorship, dict):
                    continue

                author = authorship.get("author")

                if not isinstance(author, dict):
                    continue

                display_name = author.get("display_name")

                if isinstance(display_name, str) and display_name.strip():
                    authors.append(display_name.strip())

        primary_location = item.get("primary_location")
        if not isinstance(primary_location, dict):
            primary_location = {}

        landing_page_url = primary_location.get("landing_page_url")
        if not isinstance(landing_page_url, str):
            landing_page_url = ""

        pdf_url = primary_location.get("pdf_url")
        if not isinstance(pdf_url, str):
            pdf_url = ""

        source = primary_location.get("source")
        if not isinstance(source, dict):
            source = {}

        source_name = source.get("display_name")
        if not isinstance(source_name, str):
            source_name = ""

        doi = item.get("doi")
        if not isinstance(doi, str):
            doi = ""

        openalex_id = item.get("id")
        if not isinstance(openalex_id, str):
            openalex_id = ""

        title = item.get("display_name") or item.get("title")
        if not isinstance(title, str):
            title = ""

        abstract = self._decode_abstract(item.get("abstract_inverted_index"))

        year = item.get("publication_year")
        if not isinstance(year, int):
            year = None

        relevance_score = item.get("relevance_score")
        if not isinstance(relevance_score, (int, float)):
            relevance_score = None

        cited_by_count = item.get("cited_by_count")
        if not isinstance(cited_by_count, int):
            cited_by_count = 0

        is_oa = primary_location.get("is_oa")
        if not isinstance(is_oa, bool):
            is_oa = False

        return {
            "openalex_id": openalex_id,
            "title": title.strip(),
            "authors": authors,
            "year": year,
            "date": item.get("publication_date")
            if isinstance(item.get("publication_date"), str)
            else "",
            "doi": doi,
            "abstract": abstract,
            "cited_by_count": cited_by_count,
            "is_open_access": is_oa,
            "landing_page_url": landing_page_url,
            "pdf_url": pdf_url,
            "source": source_name,
            "language": (
                item.get("language")
                if isinstance(item.get("language"), str)
                else ""
            ),
            "relevance_score": relevance_score,
        }

    @staticmethod
    def _decode_abstract(
        inverted_index: Any,
    ) -> str:
        if not isinstance(inverted_index, dict):
            return ""

        words: list[tuple[int, str]] = []

        for token, positions in inverted_index.items():
            if not isinstance(token, str):
                continue

            if not isinstance(positions, list):
                continue

            for position in positions:
                if isinstance(position, int) and position >= 0:
                    words.append((position, token))

        words.sort(key=lambda item: item[0])

        return " ".join(token for _, token in words)

    @staticmethod
    def _paper_evidence_text(
        paper: dict[str, Any],
    ) -> str:
        authors = ", ".join(paper["authors"])

        return (
            f"Title: {paper['title']}\n"
            f"Authors: {authors}\n"
            f"Year: {paper['year'] or ''}\n"
            f"DOI: {paper['doi']}\n"
            f"Journal/Source: {paper['source']}\n"
            f"OpenAlex ID: {paper['openalex_id']}\n"
            f"Cited by: {paper['cited_by_count']}\n"
            f"Open access: {paper['is_open_access']}\n"
            f"Landing page: {paper['landing_page_url']}\n"
            f"PDF: {paper['pdf_url']}\n"
            f"Abstract:\n{paper['abstract']}"
        )

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
