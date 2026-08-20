from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from core.sage import create_sage

app = FastAPI(title="Sage API", version="0.4.0")
sage = create_sage()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "sage"
    messages: list[ChatMessage]
    workload: str = "chat"
    conversation_id: str = "default"
    temperature: float | None = 0.7
    stream: bool = False


@app.get("/v1/models")
def list_models() -> dict[str, Any]:
    return {"object": "list", "data": [{"id": "sage", "object": "model", "owned_by": "sage"}]}


@app.post("/v1/chat/completions")
def chat_completions(request: ChatRequest) -> dict[str, Any]:
    if not request.messages:
        raise ValueError("No messages supplied.")
    response = sage.respond(
        [{"role": m.role, "content": m.content} for m in request.messages],
        workload=request.workload,
        conversation_id=request.conversation_id,
    )
    return {
        "id": "sage-chat",
        "object": "chat.completion",
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response},
            "finish_reason": "stop",
        }],
    }
