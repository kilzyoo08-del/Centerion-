# Centerion backend — запуск

## Состав модулей

- `chat`: Qwen-compatible text generation with recent conversation context.
- `files`: extraction and analysis for PDF, DOCX, XLSX, CSV, TXT, Markdown and common source files.
- `code`: code generation and limited static validation (Python AST and JSON parser). Generated code is never executed.
- `memory`: durable SQLite facts, chat history and task records.
- `orchestrator`: selects the core for incoming tasks.

## Kaggle setup

1. Ensure the exported model directory exists at `/kaggle/working/centerion_qwen3_4b`, or set `CENTERION_MODEL_PATH`.
2. In a Kaggle notebook terminal/cell, install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Start the API from the repository root:

```bash
export CENTERION_MODEL_PATH=/kaggle/working/centerion_qwen3_4b
export CENTERION_DB_PATH=/kaggle/working/centerion_data/centerion.sqlite3
uvicorn centerion.api:app --app-dir backend --host 0.0.0.0 --port 8000
```

4. Expose port 8000 through the already-configured ngrok tunnel. Update Android `CenterionApi.BASE_URL` if the tunnel address changes.

## API

- `GET /health`
- `POST /answer` — form fields `message`, `user_id`
- `POST /files` — multipart `file`, `question`, `user_id`
- `POST /code` — form fields `task`, `language`
- `POST /memory` — form fields `user_id`, `fact`
- `GET /memory/{user_id}`
- `POST /media` — intentionally returns HTTP 501 until a real, tested vision model is configured.

## Important limitations before production

- SQLite persistence survives process restarts only while its data directory persists. Kaggle ephemeral storage is not permanent; use persistent volume/object storage or a managed database for long-term memory.
- Vision is not implemented by this backend yet.
- Code is generated and statically checked only; it is not run in a sandbox.
- Add authentication/API keys, per-user authorization, rate limits, file scanning, quotas and HTTPS controls before public deployment.
- The Android UI currently exposes chat and photo selection. Document/code/memory backend endpoints and client methods are foundations; wire them into UI and test end-to-end before describing them as finished user features.
- Do not commit model weights, tokens, API keys or private user documents to Git.
