from __future__ import annotations

from typing import Any

from scrapling.fetchers import Fetcher, StealthyFetcher


def fetch_page(
    url: str,
    stealth: bool = False,
) -> dict[str, Any]:
    if not url.strip():
        raise ValueError("URL cannot be empty.")

    if stealth:
        page = StealthyFetcher.fetch(url)
    else:
        page = Fetcher.get(url)

    return {
        "url": url,
        "status": getattr(page, "status", None),
        "title": _extract_title(page),
        "text": _extract_text(page),
    }


def _extract_title(page: Any) -> str:
    try:
        title = page.css("title::text").get()
        return title.strip() if title else ""
    except Exception:
        return ""


def _extract_text(page: Any) -> str:
    try:
        body = page.css("body").get()
        if body:
            return str(body)
    except Exception:
        pass

    return str(page)
