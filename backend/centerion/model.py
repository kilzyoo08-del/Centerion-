"""Local Qwen3 adapter for Centerion.

The model is loaded lazily (or at startup when CENTERION_PRELOAD_MODEL=1).
Weights must be mounted locally or downloaded from the configured Hugging Face
model ID. Never put model weights or credentials in the Android APK/repository.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

_MODEL = None
_TOKENIZER = None
_LOCK = threading.Lock()
_MODEL_SOURCE: str | None = None


class ModelUnavailable(RuntimeError):
    """Raised when the configured language model cannot serve inference."""


def _resolve_source() -> str:
    explicit = os.getenv("CENTERION_MODEL_PATH", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        if path.exists():
            if path.is_file():
                path = path.parent
            if not (path / "config.json").is_file():
                raise ModelUnavailable(
                    "CENTERION_MODEL_PATH must point to a model directory containing config.json."
                )
            return str(path.resolve())
        # A non-existing path is not silently treated as a model repository.
        raise ModelUnavailable("Configured CENTERION_MODEL_PATH does not exist.")

    # Default to a staged model in the repository/project volume when present.
    project_root = Path(__file__).resolve().parents[2]
    staged = project_root / "models" / "centerion_qwen3_4b"
    if (staged / "config.json").is_file():
        return str(staged.resolve())

    # Public model ID fallback. The host downloads weights into its own cache.
    return os.getenv("CENTERION_MODEL_ID", "Qwen/Qwen3-4B").strip()


def get_status() -> dict[str, Any]:
    """Safe readiness metadata; never returns credentials or secret values."""
    loaded = _MODEL is not None and _TOKENIZER is not None
    source = _MODEL_SOURCE or os.getenv("CENTERION_MODEL_PATH") or os.getenv(
        "CENTERION_MODEL_ID", "Qwen/Qwen3-4B"
    )
    try:
        import torch
        cuda_available = bool(torch.cuda.is_available())
    except Exception:
        cuda_available = False
    return {
        "model_loaded": loaded,
        "model": "centerion",
        "model_version": "qwen3-4b",
        "model_source_configured": bool(source),
        "cuda_available": cuda_available,
    }


def load_model() -> None:
    """Load the configured model once. CPU loading is opt-in and not recommended."""
    global _MODEL, _TOKENIZER, _MODEL_SOURCE
    if _MODEL is not None and _TOKENIZER is not None:
        return

    with _LOCK:
        if _MODEL is not None and _TOKENIZER is not None:
            return

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except Exception as exc:
            raise ModelUnavailable(
                "PyTorch/Transformers is not installed in the server environment."
            ) from exc

        if not torch.cuda.is_available() and os.getenv("CENTERION_ALLOW_CPU_MODEL", "0") != "1":
            raise ModelUnavailable(
                "No CUDA GPU is available. CPU inference is disabled; set "
                "CENTERION_ALLOW_CPU_MODEL=1 only on a host with sufficient RAM."
            )

        source = _resolve_source()
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                source,
                trust_remote_code=False,
                local_files_only=os.getenv("CENTERION_LOCAL_FILES_ONLY", "0") == "1",
            )
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            model = AutoModelForCausalLM.from_pretrained(
                source,
                torch_dtype=dtype,
                device_map="auto",
                low_cpu_mem_usage=True,
                trust_remote_code=False,
                local_files_only=os.getenv("CENTERION_LOCAL_FILES_ONLY", "0") == "1",
            )
            model.eval()
        except Exception as exc:
            raise ModelUnavailable(
                "Could not load the configured Centerion language model: "
                + type(exc).__name__
            ) from exc

        _TOKENIZER = tokenizer
        _MODEL = model
        _MODEL_SOURCE = source


def generate(messages: list[dict[str, str]], max_new_tokens: int = 700) -> str:
    load_model()
    tokenizer = _TOKENIZER
    model = _MODEL

    try:
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    except TypeError:
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    import torch

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max(1, min(int(max_new_tokens), 2048)),
            do_sample=True,
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            repetition_penalty=1.05,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated = output[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()
