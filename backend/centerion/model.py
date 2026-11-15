"""Lazy Qwen-compatible text model adapter. Model files stay outside the APK."""
from __future__ import annotations
import os
import threading

_MODEL = None
_TOKENIZER = None
_LOCK = threading.Lock()


def _load():
    global _MODEL, _TOKENIZER
    if _MODEL is not None and _TOKENIZER is not None:
        return _MODEL, _TOKENIZER
    with _LOCK:
        if _MODEL is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            model_id = os.getenv("CENTERION_MODEL_PATH", "/kaggle/working/centerion_qwen3_4b")
            _TOKENIZER = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            _MODEL = AutoModelForCausalLM.from_pretrained(
                model_id, torch_dtype=dtype, device_map="auto", trust_remote_code=True
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
