from __future__ import annotations

import json
from typing import Any

from ddgs import DDGS

from sage_mcp.client import call_tool


def _wigolo_search(
    query: str,
    max_results: int,
) -> list[dict[str, Any]]:
    result = call_tool(
        "search",
        {
            "query": query,
            "max_results": max_results,
        },
        server="wigolo",
    )

    structured = getattr(result, "structured_content", None)

    if isinstance(structured, dict):
        payload: Any = structured.get("result", structured)
    else:
        content = getattr(result, "content", None) or []
        if not content:
            return []

        text = getattr(content[0], "text", "")
        if not text:
            return []

        payload = json.loads(text)

    if not isinstance(payload, dict):
        return []

    raw_results = payload.get("results", [])
    if not isinstance(raw_results, list):
        return []

    results: list[dict[str, Any]] = []

    for item in raw_results[:max_results]:
        if not isinstance(item, dict):
            continue

        results.append(
            {
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "snippet": str(
                    item.get("snippet")
                    or item.get("excerpt")
                    or ""
                ),
                "relevance_score": item.get("relevance_score"),
                "evidence_score": item.get("evidence_score"),
                "citation_id": item.get("citation_id"),
                "cached": item.get("cached", False),
                "cached_at": item.get("cached_at"),
                "fetch_failed": item.get("fetch_failed"),
                "content_from_snippet": item.get(
                    "content_from_snippet",
                    False,
                ),
            }
        )

    return results


def _ddgs_search(
    query: str,
    max_results: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    with DDGS() as ddgs:
        for item in ddgs.text(
            query,
            max_results=max_results,
        ):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", ""),
                    "source": "ddgs",
                }
            )

    return results


def web_search(
    query: str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("Search query cannot be empty.")

    try:
        results = _wigolo_search(query, max_results)

        if results:
            return results
    except Exception:
        pass

    return _ddgs_search(query, max_results)
