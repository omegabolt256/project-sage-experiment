from __future__ import annotations

import asyncio
from typing import Any

from browser.playwright_browser import PlaywrightBrowser


def browser_open(url: str) -> dict[str, Any]:
    """
    Open a webpage with Playwright and return its title, URL, and visible text.
    """
    return asyncio.run(
        PlaywrightBrowser().open(url)
    )
