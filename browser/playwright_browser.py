from __future__ import annotations

from dataclasses import dataclass
from playwright.async_api import async_playwright


@dataclass
class PlaywrightBrowser:
    headless: bool = True

    async def open(self, url: str) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)

            try:
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded")

                return {
                    "url": page.url,
                    "title": await page.title(),
                    "text": await page.locator("body").inner_text(),
                }
            finally:
                await browser.close()
