# Centerion — аудит объединения системы (2026-11-22)

## Краткий вывод

Основные части проекта найдены в GitHub, Deepnote и Supabase. Они пока **не являются одной полностью работающей production-системой**. Этот документ фиксирует проверенное состояние и порядок объединения без выдачи экспериментальных ядер за готовые возможности.

## Единый целевой контур

1. Android-клиент → Supabase Auth.
2. Android → Edge Function `centerion` с пользовательским JWT.
3. Edge Function проверяет пользователя и пересылает запрос в Centerion Runtime.
4. Runtime выбирает зарегистрированное специализированное ядро.
5. Пользовательская память и документы хранятся в Supabase с проверкой владельца.
6. PostHog получает только технические события без текста сообщений, содержимого файлов и секретов.
7. Deepnote остаётся средой разработки, обучения и проверки; не является постоянным публичным API.

## GitHub — основной репозиторий

Репозиторий: `kilzyoo08-del/Centerion-`, основная ветка `main`.

В текущем backend есть отдельные Chat, Files, Code, Memory и Orchestrator модули. Vision endpoint `POST /media` пока возвращает 501. Android-клиент ещё не прошёл end-to-end проверку с production runtime.

Docker runtime устанавливает только серверные зависимости из `backend/requirements-server.txt`. PyTorch/Transformers находятся отдельно в `backend/requirements-model.txt` и не входят в базовый образ. Поэтому сборка контейнера сама по себе не означает, что языковая модель установлена или загружена.

Текущий model adapter использует локальный каталог `CENTERION_MODEL_PATH`; автоматического внешнего fallback нет. При этом проверка `is_configured()` подтверждает наличие `config.json`, а не успешную загрузку весов и выполнение inference. Это необходимо учитывать в health/readiness проверках.

## Deepnote — каталог ядер и экспериментов

Основной проект: `Centerion Memory Engine — long context and reasoning training`.
- 17 notebooks в проекте и 331 файл в инвентаре на момент аудита.
- Проектная машина остановлена; тип машины — CPU Basic, 2 vCPU, 5 GiB RAM, без GPU.
- В проекте видны исходники и экспериментальные реализации семейств: language adapter, mathematics, programming, geometry/physics, science/knowledge, networking, game development, planning/reasoning, cognitive orchestration, memory/evidence, multimodal adapters и kernel registry.
- Отдельный Core Hub v1 перечисляет эти семейства и подключает их через runtime v3. Runtime v4 добавляет persistent memory и composition layer, но его языковой adapter — Qwen Transformers adapter. Это экспериментальный runtime, а не доказательство, что все ядра уже подключены к production API.

### Собственная модель и обучение

В Deepnote присутствуют небольшие Kolai checkpoint-файлы. Проверенный 3M candidate имеет около 1.97 млн уникальных параметров, файл порядка 7.9 MB и заявленный контекст 512 токенов. Это экспериментальный небольшой checkpoint, а не готовая универсальная разговорная LLM.

Аудит набора reasoning v3 показывает 84 train rows, 42 validation rows и 42 held-out test rows; 168/168 manifest oracle checks прошли. Однако обучение не запускалось. В отчёте за 2026-11-22 указано, что текущий training script рассчитан на legacy v1 dataset и не принимает новый v3 dataset без отдельного entrypoint. GPU в проверенной Deepnote-машине отсутствует.

CPU regression report от 2026-11-21 фиксирует 22/22 теста, но с `qwen_loaded=false`, `training_executed=false` и без inference. Это подтверждает тестирование защитных контрактов и изоляции, но не качество генерации ответов.

Проект `Centerion Egg Cloud` — отдельный небольшой Python notebook-проект, не production runtime.

## Supabase

Проект `tdqyhptkrmxoohfpfwvs` активен и здоров; отображаемое имя проекта — `kolai`.

- Edge Function `centerion`: ACTIVE, version 12, JWT verification включена.
- Код функции читает `CENTERION_RUNTIME_URL` и `CENTERION_RUNTIME_TOKEN` и пересылает запросы в runtime. Полное соединение считается подтверждённым только после настройки этих серверных переменных и успешного живого health/chat теста.
- Legacy function `kolai-bridge`: ACTIVE, version 2, `verify_jwt=false`. Не использовать её как публичную точку входа Android.
- Security advisor сообщил 10 INFO findings: RLS включён, но политики отсутствуют на 10 таблицах внутренних схем `centerion` и `centerion_memory`. Нужны адресные политики/ограничения по реальной модели доступа; нельзя вслепую создавать одинаковую политику для всех таблиц.
- Performance advisor сообщил 13 неиспользуемых индексов. Не удалять их автоматически без анализа запросов и нагрузки.
- Health advisor не сообщил findings в момент проверки.

Секреты и значения ключей в этот документ не включаются.

## PostHog

Проверенный проект PostHog: `Default project`, ID `710416`.

- `ingested_event=false`: PostHog не зарегистрировал ни одного события в этом проекте на момент проверки.
- Environment integrations: 0.
- В списке есть 8 стартовых шаблонных insights, но это не подтверждение аналитики Центериона.
- Поиск в основной ветке GitHub не обнаружил PostHog SDK или его инициализацию.

Следующий шаг — добавить серверную отправку минимальных технических событий (например, request accepted, core selected, request failed, latency bucket), не передавая личный текст, файлы, токены или персональные факты; затем проверить поступление тестового события.

## Текущие блокеры полного объединения

1. Railway runtime ещё не развёрнут; URL и runtime token не установлены в Supabase.
2. В базовом Docker образе нет ML dependencies и нет установленного/проверенного checkpoint.
3. Экспериментальные Deepnote ядра не перенесены и не подключены как проверяемые модули GitHub backend.
4. Собственная Kolai модель пока слишком мала и имеет короткий контекст; обучение на новом reasoning v3 наборе не запускалось.
5. Vision/ASR/TTS/video adapters требуют отдельных реальных моделей и тестов.
6. Supabase нуждается в адресном аудите RLS policies и ограничений клиентских ролей.
7. PostHog пока не получает события приложения.
8. Android CI ранее завершился ошибкой Kotlin-компиляции в `LocalVideoGenerator.kt`; в этой ветке исправляется ссылка на surface color format. Успех будет подтверждён только новым CI run.

## Безопасный порядок завершения

1. Объединить исправление Android CI и этот аудит в PR; дождаться зелёной сборки.
2. Перенести выбранные Deepnote specialist modules в GitHub как отдельные пакеты с единым контрактом, зависимостями и тестами; переносить только проверенные исходники, не `.pyc` и не checkpoints в git.
3. Добавить реестр ядер и fail-closed маршрутизацию; каждое неподключённое ядро должно возвращать `unavailable`.
4. Развернуть runtime в Railway после подключения пользователя, установить секреты только в server-side settings и подключить persistent volume.
5. Настроить Supabase Edge Function на runtime и провести живые JWT, memory ownership и chat tests.
6. Уточнить RLS для каждой таблицы и повторить security advisor.
7. Добавить PostHog server-side events и проверить первое событие.
8. Провести end-to-end тест Android → Supabase → runtime → ядро → Supabase/PostHog.
9. Только после этого считать Центерион объединённым production-приложением.

## Критерий готовности

Ни одно ядро не считается готовым по одному лишь наличию файла или записи в реестре. Требуются: импорт без ошибок, unit tests, routing test, failure test, security test и end-to-end вызов через публичный API.
