---
title: Centerion
emoji: 🧠
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Centerion — Android app and modular AI backend

Android-приложение на Kotlin + Jetpack Compose и отдельный Python backend.

## Android

- Чат отправляет текст на Centerion API через `POST /answer`.
- Можно выбрать изображение; Android-клиент отправляет его на `POST /media`.
- Вкладка генерации видео удалена.
- Методы API-клиента для документов, генерации кода и памяти добавлены, но соответствующие действия ещё не выведены в интерфейс чата.

## Backend cores

Исходники backend находятся в `backend/centerion`:

- Chat core — ответы через загруженную языковую модель.
- Files core — извлечение и анализ PDF, DOCX, XLSX, CSV, TXT, Markdown и исходного кода.
- Code core — генерация кода и ограниченная статическая проверка Python/JSON; код не запускается.
- Memory core — SQLite для истории диалога и сохранённых фактов.
- Orchestrator — маршрутизация задач к ядрам.

## Не завершено

- Vision core пока не настроено: `POST /media` возвращает HTTP 501, пока не установлена и не протестирована модель зрения.
- Android UI для загрузки документов, программирования и управления памятью ещё нужно подключить.
- Постоянное хранение за пределами Kaggle требует постоянного хранилища; локальная SQLite в эфемерной Kaggle-сессии не гарантирует сохранность после удаления runtime.
- Требуется end-to-end тестирование и защита API перед публичным использованием.

## Backend setup

Смотри [backend/README_RU.md](backend/README_RU.md).

## Сборка APK

CodeMagic workflow: `android-debug`, тип машины `mac_mini_m2`.
