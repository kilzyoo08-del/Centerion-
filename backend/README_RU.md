# Centerion — собственный сервер (Qwen3-4B)

Это серверная часть Centerion. Supabase остаётся шлюзом авторизации и хранения диалогов; FastAPI-сервер выполняет локальную генерацию ответов моделью, размещённой на сервере.

## Что исправлено в этой ветке

- Модель больше не ищется по старому пути Kaggle `/kaggle/working/...`.
- Поддерживается локальная папка модели через `CENTERION_MODEL_PATH`.
- Если локальная папка не задана, используется `CENTERION_MODEL_ID` (по умолчанию `Qwen/Qwen3-4B`).
- Для Qwen3 требуется современный Transformers (`>=4.51.0`).
- CPU-загрузка по умолчанию запрещена, чтобы случайно не запустить тяжёлую 4B-модель на неподходящем хосте.
- `/health` и `/v1/health` больше не объявляют модель готовой до фактической загрузки.
- Добавлен защищённый `POST /v1/chat`, совместимый с Supabase Edge Function `centerion`.
- Supabase передаёт память как контекст; сервер не хранит общий межпользовательский чат в локальной SQLite.
- Ответ помечается `unverified`: свободная генерация не считается проверенным фактом.

## Требования к хосту

Для Qwen3-4B рекомендуется GPU-хост с достаточной видеопамятью (ориентир — 16 GB VRAM) и постоянным диском под веса/кэш. Модель не включена в Git-репозиторий.

Deepnote CPU Basic (2 vCPU / 5 GB RAM) не подходит для этой модели. Не публикуйте API на обычном бесплатном CPU-хостинге, рассчитывая, что он сможет быстро обслуживать Qwen3-4B.

## Переменные окружения

Задайте их в панели хостинга, а не в GitHub и не в APK:

- `CENTERION_MODEL_PATH` — абсолютный путь к папке с `config.json`, tokenizer-файлами и всеми shard-файлами модели. Например: `/models/centerion_qwen3_4b`.
- Или `CENTERION_MODEL_ID` — ID модели на Hugging Face; по умолчанию `Qwen/Qwen3-4B`.
- `CENTERION_LOCAL_TOKEN` — длинный случайный секрет для входящих запросов от Supabase.
- `CENTERION_PRELOAD_MODEL=1` — загрузить модель при старте сервера; рекомендуется для production, чтобы ошибки загрузки были видны сразу.
- `CENTERION_ALLOW_CPU_MODEL=0` — оставить CPU-загрузку отключённой.
- `CENTERION_LOCAL_FILES_ONLY=1` — включить, если все файлы модели уже находятся на диске.
- `CENTERION_DB_PATH` — путь к SQLite для локальных функций памяти/файлов. Для Supabase-чата историю сохраняет сама Supabase Edge Function.

## Установка и запуск

Из корня репозитория:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
export CENTERION_MODEL_PATH=/models/centerion_qwen3_4b
export CENTERION_LOCAL_TOKEN='SET_A_LONG_RANDOM_SECRET_IN_HOSTING_PANEL'
export CENTERION_PRELOAD_MODEL=1
export CENTERION_ALLOW_CPU_MODEL=0
uvicorn centerion.api:app --app-dir backend --host 0.0.0.0 --port 8766
```

На GPU-хосте установите CUDA-совместимую сборку PyTorch, соответствующую драйверу и окружению хоста, до запуска приложения.

## API

- `GET /` — сведения о сервисе.
- `GET /health` и `GET /v1/health` — состояние API и реальная готовность модели.
- `POST /v1/chat` — JSON: `message`, необязательные `conversation_id`, `request_id`, `context.memory_context`; заголовок `Authorization: Bearer <CENTERION_LOCAL_TOKEN>`.
- `POST /answer` — старый Android-совместимый multipart/form endpoint.
- `POST /files` — извлечение и анализ PDF/DOCX/XLSX/CSV/TXT и исходных файлов.
- `POST /code` — генерация кода и ограниченная статическая проверка; код не исполняется.
- `POST /memory`, `GET /memory/{user_id}` — локальная SQLite-память старого API.
- `POST /media` — пока возвращает 501: модель зрения не подключена.

## Подключение Supabase

В Edge Function `centerion` уже предусмотрена отправка запроса на `CENTERION_KOLAI_URL + /v1/chat` с Bearer-токеном из `CENTERION_KOLAI_TOKEN`.

После запуска сервера задайте в Supabase Edge Function secrets:

- `CENTERION_KOLAI_URL` — публичный HTTPS base URL сервера, без завершающего слэша.
- `CENTERION_KOLAI_TOKEN` — то же значение, что `CENTERION_LOCAL_TOKEN` на сервере.

Не отключайте JWT-проверку Supabase. Не передавайте service-role key или model token в Android. После задания secrets проверьте `GET /functions/v1/centerion/v1/health`: ожидается `status: ok` и `model_loaded: true`.

## Важные ограничения

- Эта ветка содержит исправления кода, но сама по себе не создаёт облачный сервер и не запускает модель.
- Весов модели нет в GitHub; их нужно смонтировать на сервер или скачать при первом старте.
- Для публичного запуска необходим HTTPS, защита секретом, ограничение частоты запросов, мониторинг и постоянный диск.
- Vision-ядро и запуск пользовательского кода в изолированной песочнице здесь не включены.
- Свободные ответы модели не маркируются как verified без независимой проверки.
