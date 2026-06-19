# Food AI MVP Backend

Backend MVP на **Python FastAPI** для дневника питания:

- Firebase Auth через Bearer ID token.
- Firestore как основная БД.
- LLM-провайдер через OpenAI-compatible API для структурированного разбора текста/фото еды.
- Supabase Storage для приватных фото.
- Фото конвертируются в WebP, качество 75%, максимум 1200px по большей стороне, метаданные вычищаются.
- Signed URLs возвращаются сразу в API responses.
- Ручное редактирование приема пищи и продуктов.
- Много приемов одного типа в день, включая много снеков.
- Если ИИ не справился после всех ретраев, backend возвращает честную ошибку: `Мы проебались, Босс.`

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполнить `.env`:

```env
FIREBASE_PROJECT_ID=...
FIREBASE_CREDENTIALS_PATH=./firebase-service-account.json
SUPABASE_URL=...
SUPABASE_SECRET_KEY=sb_secret_...
SUPABASE_STORAGE_BUCKET=meal-photos
LLM_BASE_URL=... # необязательно; пусто = дефолтный OpenAI endpoint
LLM_API_KEY=...
LLM_MODEL=...
```

Запуск:

```bash
uvicorn app.main:app --reload
```

Healthcheck:

```bash
curl http://localhost:8000/health
```

## Firebase

Frontend должен отправлять Firebase ID token:

```http
Authorization: Bearer <firebase-id-token>
X-Timezone: Europe/Helsinki
```

Backend сам берет `uid` из токена. Не передавайте `uid` в body.

## Supabase Storage

Создайте private bucket, например `meal-photos`.

Backend использует новый Supabase `SUPABASE_SECRET_KEY` (`sb_secret_...`), поэтому ключ должен жить только на backend. Legacy `SUPABASE_SERVICE_ROLE_KEY` принимается только как временный fallback для старых проектов.


## LLM provider / кастомный URL

Если используешь не OpenAI, а OpenAI-compatible endpoint, добавь URL в `.env`:

```env
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=your-provider-key
LLM_MODEL=your-food-vision-model
LLM_RECOMMENDATION_MODEL=your-text-model
```

Важно: у некоторых провайдеров `/v1` должен быть частью `LLM_BASE_URL`, а некоторые ждут URL без `/v1`. Смотри документацию конкретного провайдера.

Код, который это читает:

- `app/core/config.py` — настройки `llm_base_url`, `llm_api_key`, `llm_model`;
- `app/llm/client.py` — создание клиента `OpenAI(base_url=...)`.

Legacy-переменные `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` тоже принимаются, но новые имена в проекте — `LLM_*`.

## Основные endpoints

### Профиль

```http
GET /v1/users/me
PATCH /v1/users/me
```

Body для timezone:

```json
{
  "timezone": "Europe/Helsinki"
}
```

### Создать прием пищи

`multipart/form-data`:

```http
POST /v1/meals
Authorization: Bearer <token>
X-Timezone: Europe/Helsinki
Content-Type: multipart/form-data
```

Fields:

- `description`: текст, что пользователь съел.
- `photo`: необязательное фото.

Пример:

```bash
curl -X POST http://localhost:8000/v1/meals \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timezone: Europe/Helsinki" \
  -F "description=омлет из двух яиц, хлеб и кофе с молоком" \
  -F "photo=@./meal.jpg"
```

Если LLM timeout / ошибка / невалидный JSON и ретраи закончились:

```json
{
  "detail": "Мы проебались, Босс."
}
```

HTTP status: `503`.

### Сегодня

```http
GET /v1/meals/today
```

Возвращает:

- сумму калорий за день;
- сумму по каждому типу приема пищи;
- список сегодняшних приемов;
- signed URLs для фото, если они есть.

### День

```http
GET /v1/meals/by-day?date=2026-06-19
```

### Один прием пищи

```http
GET /v1/meals/{meal_id}
```

### Ручная правка

```http
PATCH /v1/meals/{meal_id}
```

Пример смены типа:

```json
{
  "meal_type": "snacks"
}
```

Пример ручной правки продуктов:

```json
{
  "items": [
    {
      "product_name": "омлет",
      "portion_g": 180,
      "kcal_per_100g": 154,
      "confidence": 1
    },
    {
      "product_name": "хлеб",
      "portion_g": 40,
      "kcal_per_100g": 250,
      "confidence": 1
    }
  ]
}
```

Backend сам пересчитает calories и totals.

Для снеков можно вручную изменить время:

```json
{
  "meal_type": "snacks",
  "consumed_at": "2026-06-19T21:30:00+03:00"
}
```

Для не-снеков ручная смена `consumed_at` запрещена.

### Удалить прием пищи

```http
DELETE /v1/meals/{meal_id}
```

Фото из Supabase Storage тоже удаляется.

### Статистика

```http
GET /v1/stats?date_from=2026-06-01&date_to=2026-06-19
```

Метрики:

- total calories;
- avg calories per day;
- avg calories per meal;
- calories by day;
- calories by meal type;
- top products by frequency;
- top products by calories;
- avg products per meal;
- avg weight per meal.

### Рекомендации

```http
POST /v1/recommendations
```

Backend берет последние 7 дней питания и отправляет отдельный prompt в OpenAI.

## Firestore структура

```text
users/{uid}
  uid
  email
  timezone
  created_at
  updated_at

users/{uid}/meals/{mealId}
  id
  uid
  description
  meal_type
  date_local
  consumed_at
  created_at
  updated_at
  photo.storage_path
  photo.width
  photo.height
  items[]
  totals
  llm
```

## Meal types

```text
breakfast          завтрак
second_breakfast   второй завтрак
lunch              обед
afternoon_snack    полдник
dinner             ужин
snacks             снеки
```

Автоназначение по локальному времени пользователя:

```text
05:00-10:29 breakfast
10:30-11:59 second_breakfast
12:00-15:29 lunch
15:30-17:29 afternoon_snack
17:30-04:59 dinner
```

`snacks` выставляется вручную.

## Архитектура

```text
app/
  main.py
  api/v1/router.py
  auth/dependencies.py
  common/
    enums.py
    time.py
    http.py
  core/
    config.py
    firebase.py
  db/firestore_refs.py
  llm/
    client.py
    prompts.py
    schemas.py
    exceptions.py
  storage/
    images.py
    supabase_storage.py
  meals/
    router.py
    service.py
    repository.py
    context.py
    calculations.py
    serializers.py
    models.py
  stats/
    router.py
    service.py
    models.py
  recommendations/
    router.py
    service.py
    models.py
  users/
    router.py
    service.py
    models.py
```

## Docker

```bash
docker compose up --build
```

## Production notes

1. `SUPABASE_SECRET_KEY` нельзя отдавать фронту. Он заменяет legacy `service_role` для backend-операций.
2. Firebase service account нельзя коммитить.
3. Bucket лучше держать private.
4. Signed URLs короткоживущие, сейчас по умолчанию 3600 секунд.
5. При AI failure запись в Firestore не создается.
6. Если фото уже было загружено, но AI упал, backend пытается удалить orphan-файл.
