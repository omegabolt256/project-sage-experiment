from __future__ import annotations

from memory.manager import MemoryManager


def _text(value: object) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return str(value).lower()

    return str(value).strip()


def remember(
    memory: object = None,
    key: object = None,
    value: object = None,
    **kwargs: object,
) -> str:
    parts: list[str] = []

    memory_text = _text(memory)
    key_text = _text(key)
    value_text = _text(value)

    if memory_text:
        parts.append(memory_text)

    if key_text and value_text:
        parts.append(f"{key_text}: {value_text}")
    elif value_text:
        parts.append(value_text)

    for name, item in kwargs.items():
        text = _text(item)
        if text:
            parts.append(f"{name}: {text}")

    content = " ".join(parts).strip()

    if not content:
        raise ValueError("No memory content supplied.")

    manager = MemoryManager()
    return manager.remember(f"Remember this: {content}")
