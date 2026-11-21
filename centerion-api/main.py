import hmac
import os
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Centerion API",
    version="0.1.0",
    description="Backend API for the Centerion assistant.",
)

CENTERION_API_TOKEN = os.getenv("CENTERION_API_TOKEN", "")
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "").rstrip("/")
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "")


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=50)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=800, ge=1, le=4096)


async def verify_client(authorization: str | None = Header(default=None)):
    # If no token is configured, the API is open. Set CENTERION_API_TOKEN in
    # deployment settings before sharing the server publicly.
    if not CENTERION_API_TOKEN:
        return
    expected = f"Bearer {CENTERION_API_TOKEN}"
    if authorization is None or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


@app.get("/")
async def root():
    return {"name": "Centerion API", "status": "online", "version": app.version}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_configured": bool(MODEL_BASE_URL and MODEL_NAME),
    }


@app.post("/v1/chat")
async def chat(request: ChatRequest, _: None = Depends(verify_client)):
    if not MODEL_BASE_URL or not MODEL_NAME:
        raise HTTPException(
            status_code=503,
            detail="AI model is not connected yet. Configure MODEL_BASE_URL and MODEL_NAME.",
        )

    headers = {"Content-Type": "application/json"}
    if MODEL_API_KEY:
        headers["Authorization"] = f"Bearer {MODEL_API_KEY}"

    payload = {
        "model": MODEL_NAME,
        "messages": [message.model_dump() for message in request.messages],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{MODEL_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="The model provider timed out.")
    except httpx.HTTPStatusError as exc:
        # Do not expose provider response bodies or secret values to clients.
        raise HTTPException(
            status_code=502,
            detail=f"Model provider returned HTTP {exc.response.status_code}.",
        )
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=502, detail="Could not reach the model provider.")

    try:
        answer = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="Unexpected model provider response.")

    return {
        "id": data.get("id"),
        "object": "chat.completion",
        "model": data.get("model", MODEL_NAME),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": data.get("choices", [{}])[0].get("finish_reason"),
            }
        ],
    }
