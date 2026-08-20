from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI(title="Sage Memory Bridge")

LETTA_URL = "http://host.docker.internal:8283"
AGENT_ID = "agent-304e51dc-cfca-466b-8055-614c2825ddc6"
BLOCK_LABEL = "human"


@app.get("/memory")
async def get_memory():
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{LETTA_URL}/v1/agents/{AGENT_ID}/core-memory/blocks/{BLOCK_LABEL}"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    data = response.json()

    return {
        "memory": data.get("value", "")
    }


@app.patch("/memory")
async def update_memory(payload: dict):
    value = payload.get("value")

    if not isinstance(value, str):
        raise HTTPException(
            status_code=400,
            detail="value must be a string"
        )

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.patch(
            f"{LETTA_URL}/v1/agents/{AGENT_ID}/core-memory/blocks/{BLOCK_LABEL}",
            json={"value": value}
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return {
        "memory": response.json().get("value", "")
    }

