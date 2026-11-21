# GPU-enabled runtime for Centerion (Qwen3-4B).
# Set CENTERION_LOCAL_TOKEN in the Space secrets; never bake secrets into this image.
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    CENTERION_MODEL_ID=Qwen/Qwen3-4B \
    CENTERION_PRELOAD_MODEL=1 \
    CENTERION_ALLOW_CPU_MODEL=0

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/centerion /app/centerion

EXPOSE 7860

CMD ["uvicorn", "centerion.api:app", "--host", "0.0.0.0", "--port", "7860"]
