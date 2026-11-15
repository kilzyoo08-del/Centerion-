# Centerion — Android app

Android-приложение на Kotlin + Jetpack Compose.

## Текущие функции

- Чат Centerion с отправкой текстовых сообщений на сервер через `POST /answer`.
- Выбор изображения на устройстве и отправка на сервер через `POST /media`.
- Отображение выбранного изображения в переписке.
- Светлый интерфейс.

## Сервер

Приложение обращается к Centerion API. Текущий адрес ngrok прописан в `CenterionApi.kt` и является временным: после перезапуска туннеля его нужно обновить.

Ожидаемые маршруты:
- `GET /health`
- `POST /answer` — поля формы `message`, `user_id`.
- `POST /media` — multipart-поля `file`, `question`.

**Важно:** отправка фотографии из Android-клиента реализована, но полноценное распознавание изображения зависит от работающего серверного vision-модуля и должно быть проверено отдельным тестом. Нельзя считать анализ фото подтверждённым только по факту отправки файла.

## Сборка APK

Workflow CodeMagic: `android-debug`.
Тип машины: `mac_mini_m2`.
Сборка создаёт debug APK: `app/build/outputs/apk/debug/app-debug.apk`.

## Технологии

- Kotlin
- Jetpack Compose
- Android Gradle Plugin
- Centerion API
