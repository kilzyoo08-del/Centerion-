"""FastAPI entrypoint for Centerion's modular backend."""
from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, Field

from . import storage
from .compute_engine import ComputeEngine
from .orchestrator import answer, analyze_file, generate_code, choose_core

app = FastAPI(title="Centerion API", version="2.1.0")
compute_engine: ComputeEngine | None = None


@app.on_event("startup")
def startup():
    global compute_engine
    storage.initialize()
    compute_engine = ComputeEngine(max_workers=2, max_pending=32)
    compute_engine.register("system.ping", lambda _payload: {"pong": True})
    compute_engine.register("text.stats", _text_stats)


@app.on_event("shutdown")
def shutdown():
    if compute_engine is not None:
        compute_engine.close()


def _text_stats(payload: dict) -> dict:
    text = payload.get("text")
    if not isinstance(text, str) or len(text) > 20000:
        raise ValueError("text must be a string of at most 20000 characters")
    return {"characters": len(text), "words": len(text.split())}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    user_id: str = Field(default="android_user", min_length=1, max_length=128)


class CodeRequest(BaseModel):
    task: str = Field(min_length=1, max_length=12000)
    language: str = Field(default="python", max_length=40)


class MemoryRequest(BaseModel):
    user_id: str = Field(default="android_user", min_length=1, max_length=128)
    fact: str = Field(min_length=1, max_length=2000)


class ComputeTaskRequest(BaseModel):
    task_type: str = Field(min_length=1, max_length=64)
    payload: dict = Field(default_factory=dict)


@app.get("/health")
def health():
    return {
        "name": "Centerion",
        "status": "online",
        "cores": ["chat", "files", "code", "memory"],
        "compute_engine": compute_engine.health() if compute_engine else {"status": "starting"},
        "vision": "not_configured",
    }


@app.get("/compute/health")
def compute_health():
    if compute_engine is None:
        raise HTTPException(503, "Compute engine is starting.")
    return compute_engine.health()


@app.post("/compute/tasks", status_code=202)
def compute_submit(req: ComputeTaskRequest):
    if compute_engine is None:
        raise HTTPException(503, "Compute engine is unavailable.")
    try:
        return compute_engine.submit(req.task_type, req.payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))


@app.get("/compute/tasks/{task_id}")
def compute_task_status(task_id: str):
    if compute_engine is None:
        raise HTTPException(503, "Compute engine is unavailable.")
    task = compute_engine.get_task(task_id)
    if task is None:
        raise HTTPException(404, "Task not found.")
    return task


@app.post("/answer")
def chat(message: str = Form(...), user_id: str = Form("android_user")):
    if not message.strip() or len(message) > 12000:
        raise HTTPException(422, "Сообщение пустое или слишком длинное.")
    try:
        core = choose_core(message)
        return {"answer": answer(user_id, message), "core": core}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Centerion chat core unavailable: {exc}")


@app.post("/files")
async def files(file: UploadFile = File(...), question: str = Form(""), user_id: str = Form("android_user")):
    raw = await file.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(413, "Файл больше 20 МБ.")
    try:
        return analyze_file(user_id, file.filename or "upload", raw, question)
    except ValueError as exc:
        raise HTTPException(415, str(exc))
    except Exception as exc:
        raise HTTPException(503, f"Files core error: {exc}")


@app.post("/code")
def code(req: CodeRequest):
    try:
        return generate_code(req.task, req.language)
    except Exception as exc:
        raise HTTPException(503, f"Code core error: {exc}")


@app.post("/memory")
def memory(req: MemoryRequest):
    storage.remember_fact(req.user_id, req.fact)
    return {"saved": True, "facts": storage.get_facts(req.user_id)}


@app.get("/memory/{user_id}")
def memory_read(user_id: str):
    return {"facts": storage.get_facts(user_id), "history": storage.get_history(user_id)}


@app.post("/media")
async def media(file: UploadFile = File(...), question: str = Form("")):
    # Explicitly unavailable until a tested vision model is configured.
    raise HTTPException(
        501,
        "Vision core is not configured yet. Photo upload is accepted by the Android UI, but image understanding is not enabled.",
    )
