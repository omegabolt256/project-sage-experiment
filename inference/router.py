from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

import httpx
from dotenv import load_dotenv

load_dotenv()

Provider = Literal["groq", "ollama"]


@dataclass
class InferenceConfig:
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_base_url: str = "https://api.groq.com/openai/v1"
    ollama_base_url: str = "http://127.0.0.1:11434/v1"

    groq_chat_model: str = "openai/gpt-oss-20b"
    ollama_chat_model: str = "qwen2.5:3b"


class InferenceRouter:
    def __init__(self, config: InferenceConfig | None = None) -> None:
        self.config = config or InferenceConfig()

    def _client(self, provider: Provider) -> httpx.Client:
        if provider == "groq":
            if not self.config.groq_api_key:
                raise RuntimeError("GROQ_API_KEY is not configured.")

            return httpx.Client(
                base_url=self.config.groq_base_url,
                headers={
                    "Authorization": f"Bearer {self.config.groq_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=(300.0 if provider == "ollama" else 120.0),
            )

        return httpx.Client(
            base_url=self.config.ollama_base_url,
            headers={"Content-Type": "application/json"},
            timeout=(300.0 if provider == "ollama" else 120.0),
        )

    def chat(
        self,
        message: str,
        provider: Provider = "ollama",
        model: str | None = None,
        system: str | None = None,
    ) -> str:
        messages: list[dict[str, str]] = []

        if system:
            messages.append(
                {"role": "system", "content": system}
            )

        messages.append(
            {"role": "user", "content": message}
        )

        return self.chat_messages(
            messages,
            provider=provider,
            model=model,
        )

    def chat_messages(
        self,
        messages: list[dict[str, str]],
        provider: Provider = "ollama",
        model: str | None = None,
        system: str | None = None,
    ) -> str:
        if not messages:
            raise ValueError("Messages cannot be empty.")

        selected_model = (
            model
            or (
                self.config.groq_chat_model
                if provider == "groq"
                else self.config.ollama_chat_model
            )
        )

        final_messages: list[dict[str, str]] = []

        if system:
            final_messages.append(
                {
                    "role": "system",
                    "content": system,
                }
            )

        final_messages.extend(messages)

        payload = {
            "model": selected_model,
            "messages": final_messages,
            "temperature": 0.7,
        }

        with self._client(provider) as client:
            response = client.post(
                "/chat/completions",
                json=payload,
            )
            response.raise_for_status()

        data = response.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Unexpected response from {provider}: {data}"
            ) from exc


if __name__ == "__main__":
    router = InferenceRouter()

    print("=== Ollama test ===")
    print(
        router.chat(
            "Reply with exactly: SAGE LOCAL OK",
            provider="ollama",
        )
    )

    print("\n=== Groq test ===")
    print(
        router.chat(
            "Reply with exactly: SAGE GROQ OK",
            provider="groq",
        )
    )

