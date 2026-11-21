"""Local Centerion model adapter. No implicit third-party model fallback."""
from __future__ import annotations
import os
import threading
from pathlib import Path

_MODEL = None
_TOKENIZER = None
_LOCK = threading.Lock()

def configured_model_path() -> Path | None:
    raw = os.getenv("CENTERION_MODEL_PATH", "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_dir() or not (path / "config.json").is_file():
        return None
    return path

def is_configured() -> bool:
    return configured_model_path() is not None

def _load():
    global _MODEL, _TOKENIZER
    if _MODEL is not None and _TOKENIZER is not None:
        return _MODEL, _TOKENIZER
    model_path = configured_model_path()
    if model_path is None:
        raise RuntimeError("Centerion model weights are not installed in CENTERION_MODEL_PATH.")
    with _LOCK:
        if _MODEL is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            _TOKENIZER = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            _MODEL = AutoModelForCausalLM.from_pretrained(
                str(model_path), torch_dtype=dtype, device_map="auto", local_files_only=True
            )
            _MODEL.eval()
    return _MODEL, _TOKENIZER

def generate(messages: list[dict[str, str]], max_new_tokens: int = 700) -> str:
    model, tokenizer = _load()
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    import torch
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=True,
                                temperature=0.65, top_p=0.9,
                                pad_token_id=tokenizer.eos_token_id)
    generated = output[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()
