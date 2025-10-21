# 🚨 СРОЧНОЕ ИСПРАВЛЕНИЕ ПРОДАКШЕНА

## Проблема
На продакшене отсутствуют колонки для ИИ функциональности:
- `candidate_responses.mismatch_analysis`
- `candidate_responses.dialog_findings` 
- `candidate_responses.language_preference`

## Решение 1: Быстрое исправление (рекомендуется)

### Вариант A: Через Render Shell
1. Зайдите в Render Dashboard
2. Откройте ваш сервис
3. Перейдите в "Shell" 
4. Выполните команды:

```bash
# Подключиться к базе данных
psql $DATABASE_URL

# Добавить недостающие колонки
ALTER TABLE candidate_responses ADD COLUMN IF NOT EXISTS mismatch_analysis JSONB;
ALTER TABLE candidate_responses ADD COLUMN IF NOT EXISTS dialog_findings JSONB;
ALTER TABLE candidate_responses ADD COLUMN IF NOT EXISTS language_preference VARCHAR(5) DEFAULT 'ru';

# Проверить результат
\d candidate_responses

# Выйти
\q
```

### Вариант B: Через Python скрипт
1. Загрузите файл `backend/scripts/quick_fix_production.py` на сервер
2. Выполните:

```bash
python3 quick_fix_production.py
```

## Решение 2: Через миграцию Alembic

1. Загрузите файл `backend/alembic/versions/add_ai_columns_to_responses.py`
2. Выполните:

```bash
alembic upgrade head
```

## Решение 3: Временное исправление (уже применено)

Код уже модифицирован для работы без этих колонок с fallback логикой.

## Проверка исправления

После применения любого из решений проверьте:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://mylink-trn6.onrender.com/responses?vacancy_id=YOUR_VACANCY_ID"
```

Должен вернуть 200 OK вместо 500 Internal Server Error.

## Приоритет исправления

1. **СРОЧНО**: Решение 1A (через psql) - самое быстрое
2. **Альтернатива**: Решение 1B (Python скрипт) 
3. **Долгосрочно**: Решение 2 (миграция)

## После исправления

1. Перезапустите сервис на Render
2. Проверьте работу ИИ чатов
3. Убедитесь, что все функции работают корректно

---
**Время исправления**: ~2-3 минуты
**Сложность**: Низкая
**Риск**: Минимальный
