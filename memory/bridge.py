from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class MemoryBridge:
    base_url: str = "http://127.0.0.1:4010"

    def get(self) -> str:
        response = httpx.get(
            f"{self.base_url}/memory",
            timeout=15.0,
        )
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise RuntimeError("Invalid memory bridge response.")

        memory = data.get("memory", "")

        if not isinstance(memory, str):
            raise RuntimeError("Memory bridge returned invalid memory data.")

        return memory

    def update(self, memory: str) -> str:
        if not isinstance(memory, str):
            raise TypeError("memory must be a string.")

        response = httpx.patch(
            f"{self.base_url}/memory",
            json={"memory": memory},
            timeout=15.0,
        )
        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict) and isinstance(data.get("memory"), str):
            return data["memory"]

        return memory


if __name__ == "__main__":
    bridge = MemoryBridge()

    print("=== Current memory ===")
    print(bridge.get())