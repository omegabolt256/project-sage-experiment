from __future__ import annotations

from typing import Any

from scrapling.fetchers import Fetcher, StealthyFetcher

from tools.web import web_search


def search_web(
    query: str,
    max_results: int = 5,
) -> list[dict[str, str]]:
    return web_search(query, max_results)


def fetch_web(
    url: str,
    stealth: bool = False,
) -> dict[str, Any]:
    if not url.strip():
        raise ValueError("URL cannot be empty.")

    page = (
        StealthyFetcher.fetch(url)
        if stealth
        else Fetcher.get(url)
    )

    title = ""
    try:
        title = page.css("title::text").get() or ""
    except Exception:
        pass

    try:
        text = page.get_all_text(
            ignore_tags=("script", "style"),
            strip=True,
        )
    except Exception:
        text = ""

    return {
        "url": url,
        "status": getattr(page, "status", None),
        "title": title.strip(),
        "text": text,
    }
