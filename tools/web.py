from __future__ import annotations

from ddgs import DDGS


def web_search(
    query: str,
    max_results: int = 5,
) -> list[dict[str, str]]:
    if not query.strip():
        raise ValueError("Search query cannot be empty.")

    results: list[dict[str, str]] = []

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
                }
            )

    return results
