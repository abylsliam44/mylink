SmartBot HR — AI‑powered Screening Platform

Overview
SmartBot автоматически анализирует отклики на вакансии, задаёт уточняющие вопросы и считает релевантность кандидатов. Проект состоит из FastAPI‑бэкенда и React‑фронтенда. Есть локальный запуск через Docker и самостоятельная сборка.

Основные возможности
- Публикация вакансий работодателем (панель работодателя)
- Публичный каталог вакансий для соискателей
- Отклик с загрузкой PDF‑резюме (поддержка PDF → текст + OCR)
- ИИ‑пайплайн: выявление несоответствий → уточняющие вопросы → скоринг → сводка
- Веб‑виджет диалога (кандидат ↔ бот)

Технологии
- Backend: FastAPI, SQLAlchemy (PostgreSQL), Redis, LangChain + OpenAI
- PDF → текст: PyPDF → pdfminer → OCR (Tesseract + pdf2image)
- Frontend: React + Vite, Tailwind‑стили; WebSocket‑подготовка (в перспективе)
- Контейнеризация: Docker Compose

Архитектура директорий
- backend/ — API, модели, агенты, сервисы
- frontend/ — клиентское приложение
- docker-compose.yml — локальный запуск (db, redis, backend, frontend)

Быстрый старт (Docker)
1) Заполните переменные окружения (пример):
- Backend (docker-compose.yml → service backend → environment):
  - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/smartbot_db
  - DATABASE_URL_SYNC=postgresql://postgres:postgres@db:5432/smartbot_db
  - REDIS_URL=redis://redis:6379/0
  - SECRET_KEY=change_me
  - ALLOWED_ORIGINS=http://localhost:8011
  - OPENAI_API_KEY=sk-...
  - OPENAI_MODEL=gpt-4o-mini

2) Запуск:
```
docker compose up --build -d
```
Backend: http://localhost:8010 (FastAPI), Frontend: http://localhost:8011

Локальный запуск без Docker (опционально)
- Backend:
  - Python 3.11
  - pip install -r backend/requirements.txt
  - uvicorn app.main:app --host 0.0.0.0 --port 8000
- Frontend:
  - npm ci
  - npm run dev

Аутентификация
- Работодатель: JWT (эндпоинты /auth, /employers)
- Клиентский токен сохраняется на фронте; панель работодателя фильтрует вакансии по текущему employer_id

Публичные и приватные эндпоинты
- GET /vacancies/public — список всех вакансий (для каталога соискателя)
- GET /vacancies — вакансии текущего работодателя (требуется Bearer)
- GET /responses?vacancy_id=... — отклики по вакансиям работодателя
- POST /candidates/upload_pdf — загрузка PDF резюме (извлечение текста с fallback на OCR)

ИИ‑пайплайн (внутренний маршрут)
- POST /ai/pipeline/screen_by_ids
  - Вход: vacancy_id, candidate_id, response_id
  - Действия: mismatch → clarifier → orchestrator → scorer
- POST /ai/mismatch
  - Вход: job_text, cv_text, (опц.) cv_pdf_b64, hints
  - Детектор добавляет извлечённый из PDF текст к cv_text перед анализом

Агенты и их правила (кратко)
- Mismatch Detector: нормализация JD/CV; извлечение skills/exp/langs/location/salary; доказательства ≤12 слов; не выдумывает; умеет искать must_have навыки как точные токены в полном тексте CV
- Clarifier: генерирует ≤3 коротких уточнения по приоритетам (skills/experience/location/langs/comp)
- Widget Orchestrator: задаёт вопросы, валидирует ответы, формирует dialogFindings
- Relevance Scorer: считает проценты по критериям; веса auto; вердикт 0–30 не подходит, 31–50 сомнительно, >50 подходит; добирает навыки из notes при пустом списке

OCR: как это работает
Порядок извлечения текста из PDF: PyPDF → pdfminer.six → Tesseract (eng+rus) через pdf2image. OCR включается, если предыдущие методы вернули слишком мало текста.

Фронтенд
- Вход для работодателя: /employer-admin
- Каталог вакансий (для соискателей): / (использует /vacancies/public)
- KPI/диаграммы: пороги согласованы со скорером (0–30/31–50/>50)

Переменные окружения (backend)
- DATABASE_URL, DATABASE_URL_SYNC, REDIS_URL — соединения к БД и Redis
- SECRET_KEY — JWT
- ALLOWED_ORIGINS — CORS
- OPENAI_API_KEY, OPENAI_MODEL — доступ к LLM

Переменные окружения (frontend)
- VITE_API_BASE — URL бэкенда (в Docker уже настроено на http://backend:8000)

Сценарии эксплуатации
- Создать работодателя → войти → создать вакансию (указать stack)
- Соискатель загружает PDF либо заполняет форму → система создаёт кандидата и отклик
- Работодатель запускает анализ (кнопка “Запустить ИИ”) → получает общий матч и разбор по критериям

Сборка и деплой (кратко)
- Docker: собрать образы и стартануть compose (см. выше)
- Render/другой PaaS: бэкенд — FastAPI web service; фронтенд — статический билд dist

Лицензия
MIT (если требуется иное — обновите секцию)


