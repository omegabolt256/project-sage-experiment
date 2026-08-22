from __future__ import annotations

from typing import Any

from scrapling.fetchers import Fetcher, StealthyFetcher

from tools.web import web_search


def search_web(
    query: str,
    max_results: int = 5,
) -> list[dict[str, str]]:
    return web_search(query, max_results)



def download_pdf(
    url: str,
    destination: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Download and validate a real PDF from an HTTP(S) URL."""

    import requests
    from pathlib import Path

    if not url.strip():
        raise ValueError("URL cannot be empty.")

    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/151.0 Safari/537.36"
            )
        },
        allow_redirects=True,
        stream=True,
    )
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()

    with response.raw as raw:
        header = raw.read(8)

    if not header.startswith(b"%PDF-"):
        raise ValueError(
            "URL did not return a valid PDF. "
            f"Content-Type={content_type!r}, "
            f"Header={header!r}"
        )

    with requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/151.0 Safari/537.36"
            )
        },
        allow_redirects=True,
        stream=True,
    ) as download:
        download.raise_for_status()

        with destination_path.open("wb") as output:
            for chunk in download.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)

    size = destination_path.stat().st_size

    if size < 1024:
        destination_path.unlink(missing_ok=True)
        raise ValueError(
            f"Downloaded PDF is suspiciously small: {size} bytes."
        )

    return {
        "path": str(destination_path),
        "url": str(response.url),
        "status": response.status_code,
        "content_type": content_type,
        "bytes": size,
    }

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
