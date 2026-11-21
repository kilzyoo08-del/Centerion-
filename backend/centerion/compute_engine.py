"""Centerion virtual compute engine.

This is a bounded application-level compute runtime, not a hardware hypervisor.
It schedules registered internal handlers and never executes submitted source code.
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import Any, Callable


@dataclass
class TaskRecord:
    task_id: str
    task_type: str
    status: str
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None
    result: Any = None
    error: str | None = None


Handler = Callable[[dict[str, Any]], Any]


class ComputeEngine:
    """Bounded scheduler for trusted, registered Centerion task handlers."""

    def __init__(self, max_workers: int = 2, max_pending: int = 32) -> None:
        if not 1 <= max_workers <= 32:
            raise ValueError("max_workers must be between 1 and 32")
        if not 1 <= max_pending <= 1000:
            raise ValueError("max_pending must be between 1 and 1000")
        self.max_workers = max_workers
        self.max_pending = max_pending
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="centerion-compute"
        )
        self._handlers: dict[str, Handler] = {}
        self._tasks: dict[str, TaskRecord] = {}
        self._futures: dict[str, Future[Any]] = {}
        self._lock = threading.RLock()
        self._closed = False

    def register(self, task_type: str, handler: Handler) -> None:
        if not task_type or len(task_type) > 64:
            raise ValueError("Invalid task type")
        with self._lock:
            if self._closed:
                raise RuntimeError("Compute engine is closed")
            self._handlers[task_type] = handler

    def submit(self, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._closed:
                raise RuntimeError("Compute engine is closed")
            handler = self._handlers.get(task_type)
            if handler is None:
                raise ValueError("Unsupported task type")
            active = sum(
                task.status in {"queued", "running"} for task in self._tasks.values()
            )
            if active >= self.max_workers + self.max_pending:
                raise RuntimeError("Compute queue is full")

            task_id = uuid.uuid4().hex
            record = TaskRecord(
                task_id=task_id,
                task_type=task_type,
                status="queued",
                created_at=time.time(),
            )
            self._tasks[task_id] = record
            future = self._executor.submit(self._run, task_id, handler, dict(payload))
            self._futures[task_id] = future
            return asdict(record)

    def _run(self, task_id: str, handler: Handler, payload: dict[str, Any]) -> None:
        with self._lock:
            record = self._tasks[task_id]
            record.status = "running"
            record.started_at = time.time()
        try:
            result = handler(payload)
            with self._lock:
                record.result = result
                record.status = "succeeded"
        except Exception as exc:
            with self._lock:
                record.error = f"{type(exc).__name__}: {exc}"[:500]
                record.status = "failed"
        finally:
            with self._lock:
                record.finished_at = time.time()

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._tasks.get(task_id)
            return asdict(record) if record else None

    def health(self) -> dict[str, Any]:
        with self._lock:
            counts = {name: 0 for name in ("queued", "running", "succeeded", "failed")}
            for record in self._tasks.values():
                counts[record.status] = counts.get(record.status, 0) + 1
            return {
                "engine": "Centerion Virtual Compute Engine",
                "status": "online" if not self._closed else "stopped",
                "workers": self.max_workers,
                "max_pending": self.max_pending,
                "cpu_count": os.cpu_count() or 1,
                "tasks": counts,
                "registered_task_types": sorted(self._handlers),
            }

    def close(self, wait: bool = True) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=not wait)
