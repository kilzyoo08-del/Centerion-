# Centerion API

A small FastAPI backend for the Centerion project. It provides a chat endpoint and forwards requests to an **OpenAI-compatible model API**. The backend does not contain or host a language model by itself.

## Endpoints

- `GET /` — service information
- `GET /health` — health check and model configuration status
- `POST /v1/chat` — chat completion

## Run locally

Python 3.11 or newer is recommended.

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Environment variables

Configure these in the hosting provider's secret/environment settings:

- `MODEL_BASE_URL` — base URL of an OpenAI-compatible API, without the final `/chat/completions` path
- `MODEL_NAME` — model identifier accepted by that provider
- `MODEL_API_KEY` — provider key (keep secret; never commit it to GitHub)
- `CENTERION_API_TOKEN` — optional token required by clients calling this backend

If `CENTERION_API_TOKEN` is empty, client authentication is disabled. Set a strong random value before making the service public.

## Deploy on Render

Create a **Web Service** from this GitHub repository and set:

- Root Directory: `centerion-api`
- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Add the environment variables above in Render's Environment settings. Start by setting the model provider variables only when you have a provider and permission to use its API.

## Important

Deploying this backend does not provide free AI inference. A separate model provider or your own model server is required. Free hosting tiers may sleep, restart, or have usage limits. Never put provider API keys in the Android app or in public source code.
