FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CENTERION_DB_PATH=/data/centerion.sqlite3

WORKDIR /app
COPY backend/requirements-server.txt /app/requirements-server.txt
RUN pip install --no-cache-dir -r /app/requirements-server.txt
COPY backend/centerion /app/backend/centerion
RUN mkdir -p /data /models/centerion

ENV PYTHONPATH=/app/backend
CMD ["sh", "-c", "uvicorn centerion.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
