from __future__ import annotations

from typing import Any

import httpx


class MinerUClient:
    """
    Local MinerU/llama.cpp completion backend.

    This does not pretend to parse PDFs directly. It accepts extracted
    document text and asks the local MinerU model to analyze/restructure it.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        timeout: float = 180.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(
        self,
        text: str,
        instruction: str = "",
        max_tokens: int = 2048,
    ) -> str:
        if not text.strip():
            raise ValueError("MinerU input text cannot be empty.")

        prompt = (
            "You are a document analysis engine.\n\n"
            "TASK:\n"
            f"{instruction.strip() or 'Analyze and structure the document text.'}\n\n"
            "DOCUMENT:\n"
            f"{text}\n\n"
            "Return only the useful structured result."
        )

        payload: dict[str, Any] = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": 0.1,
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/completion",
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        content = data.get("content", "")

        if not isinstance(content, str):
            raise RuntimeError(
                f"Unexpected MinerU response: {data}"
            )

        return content.strip()
