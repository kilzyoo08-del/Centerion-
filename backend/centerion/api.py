"""Authenticated internal FastAPI runtime for Centerion."""
from __future__ import annotations

import hmac
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import storage
from .model import is_configured
from .orchestrator import answer, analyze_file, generate_code, choose_core

app = FastAPI(title="Centerion Runtime", version="2.1.0", docs_url=None, redoc_url=None, openapi_url=None)

@app.on_event("startup")
def startup():
    storage.initialize()

@app.middleware("http")
async def internal_runtime_auth(request: Request, call_next):
    if request.url.path in {"/health", "/v1/health"}:
        return await call_next(request)
    expected = os.getenv("CENTERION_RUNTIME_TOKEN", "").strip()
    supplied = request.headers.get("x-centerion-runtime-token", "")
    if not expected:
        return JSONResponse(status_code=503, content={"error": "runtime_token_not_configured"})
    if not supplied or not hmac.compare_digest(supplied, expected):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return await call_next(request)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    user_id: str = Field(min_length=1, max_length=128)
    context: dict = Field(default_factory=dict)

class CodeRequest(BaseModel):
    task: str = Field(min_length=1, max_length=12000)
    language: str = Field(default="python", max_length=40)

class MemoryRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    fact: str = Field(min_length=1, max_length=2000)

def health_payload():
    ready = is_configured()
    return {
        "name": "Centerion",
        "status": "ok" if ready else "degraded",
        "model_loaded": ready,
        "memory_ready": True,
        "reason": "centerion_model_ready" if ready else "centerion_model_not_configured",
        "cores": {"chat": ready, "files": ready, "code": ready, "memory": True, "vision": False},
    }

@app.get("/health")
@app.get("/v1/health")
def health():
    return health_payload()

@app.get("/v1/kernels")
def kernels():
    state = health_payload()
    return {"kernels": [{"id": name, "available": available} for name, available in state["cores"].items()]}

@app.post("/v1/chat")
def chat_v1(req: ChatRequest):
    if not is_configured():
        raise HTTPException(status_code=503, detail="Centerion inference model is not configured.")
    try:
        result = answer(req.user_id, req.message, str(req.context.get("memory_context", "")))
        return {"answer": result, "model": {"name": "Centerion", "version": "runtime-v1"},
                "verification_status": "unverified", "tool_summary": []}
    except Exception:
        raise HTTPException(status_code=503, detail="Centerion chat core unavailable.")

@app.post("/v1/kernels/{kernel_id}")
def run_kernel(kernel_id: str, req: ChatRequest):
    if kernel_id not in {"chat", "code", "files", "memory"}:
        raise HTTPException(status_code=404, detail="Unknown Centerion core.")
    if not is_configured() and kernel_id != "memory":
        raise HTTPException(status_code=503, detail="Centerion inference model is not configured.")
    if kernel_id == "chat":
        return {"answer": answer(req.user_id, req.message, str(req.context.get("memory_context", ""))), "core": "chat"}
    if kernel_id == "code":
        return generate_code(req.message, "python")
    if kernel_id == "memory":
        storage.remember_fact(req.user_id, req.message)
        return {"saved": True}
    raise HTTPException(status_code=501, detail="Files core requires a file upload.")

@app.post("/answer")
def chat_form(message: str = Form(...), user_id: str = Form(...)):
    if not is_configured():
        raise HTTPException(status_code=503, detail="Centerion inference model is not configured.")
    if not message.strip() or len(message) > 12000:
        raise HTTPException(422, "Сообщение пустое или слишком длинное.")
    try:
        return {"answer": answer(user_id, message), "core": choose_core(message)}
    except Exception:
        raise HTTPException(status_code=503, detail="Centerion chat core unavailable.")

@app.post("/files")
async def files(file: UploadFile = File(...), question: str = Form(""), user_id: str = Form(...)):
    raw = await file.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(413, "Файл больше 20 МБ.")
    if not is_configured():
        raise HTTPException(status_code=503, detail="Centerion inference model is not configured.")
    try:
        return analyze_file(user_id, file.filename or "upload", raw, question)
    except ValueError as exc:
        raise HTTPException(415, str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="Files core unavailable.")

@app.post("/code")
def code(req: CodeRequest):
    if not is_configured():
        raise HTTPException(status_code=503, detail="Centerion inference model is not configured.")
    try:
        return generate_code(req.task, req.language)
    except Exception:
        raise HTTPException(status_code=503, detail="Code core unavailable.")

@app.post("/memory")
def memory(req: MemoryRequest):
    storage.remember_fact(req.user_id, req.fact)
    return {"saved": True, "facts": storage.get_facts(req.user_id)}

@app.get("/memory/{user_id}")
def memory_read(user_id: str):
    return {"facts": storage.get_facts(user_id), "history": storage.get_history(user_id)}

@app.post("/media")
async def media(file: UploadFile = File(...), question: str = Form("")):
    raise HTTPException(501, "Centerion vision core is not configured yet.")
