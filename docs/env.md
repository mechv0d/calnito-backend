# Переменные окружения

Файл: `.env`

## Минимальный пример

```env
APP_NAME=Food AI MVP Backend
APP_ENV=local
API_PREFIX=/v1
CORS_ORIGINS=*

FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_CREDENTIALS_PATH=./firebase-service-account.json
FIREBASE_CHECK_REVOKED=false

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=sb_secret_your-secret-key
SUPABASE_STORAGE_BUCKET=meal-photos
SIGNED_URL_EXPIRES_SECONDS=3600

LLM_BASE_URL=https://your-openai-compatible-provider.example/v1
LLM_API_KEY=your-llm-key
LLM_MODEL=your-food-vision-model
LLM_RECOMMENDATION_MODEL=your-text-model
LLM_TIMEOUT_SECONDS=45
LLM_MAX_RETRIES=1

DEFAULT_TIMEZONE=UTC
MAX_UPLOAD_BYTES=10485760
MAX_IMAGE_SIDE_PX=1200
WEBP_QUALITY=75
USER_FACING_AI_ERROR=Мы проебались, Босс.
```

## Firebase

| Переменная | Обязательна | Описание |
|---|---:|---|
| `FIREBASE_PROJECT_ID` | желательно | ID Firebase проекта. |
| `FIREBASE_CREDENTIALS_PATH` | один из способов | Путь к service account JSON. |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | один из способов | Service account JSON строкой. Удобно для deploy. |
| `FIREBASE_CHECK_REVOKED` | нет | Проверять ли revoked tokens. Для MVP обычно `false`. |

## Supabase

| Переменная | Обязательна | Описание |
|---|---:|---|
| `SUPABASE_URL` | да | URL проекта Supabase. |
| `SUPABASE_SECRET_KEY` | да | Новый server-side key формата `sb_secret_...`. Только backend. |
| `SUPABASE_STORAGE_BUCKET` | да | Private bucket для фото еды. Например `meal-photos`. |
| `SIGNED_URL_EXPIRES_SECONDS` | нет | Срок жизни signed URL в секундах. По умолчанию `3600`. |

`SUPABASE_SERVICE_ROLE_KEY` в проекте может читаться как legacy fallback, но для нового проекта используй именно `SUPABASE_SECRET_KEY`.

## LLM provider

Проект использует OpenAI-compatible клиент, но endpoint может быть кастомным.

| Переменная | Обязательна | Описание |
|---|---:|---|
| `LLM_BASE_URL` | нет | Кастомный base URL. Например `https://provider.example/v1`. Если пусто — дефолтный endpoint SDK. |
| `LLM_API_KEY` | да | API key LLM-провайдера. |
| `LLM_MODEL` | да | Модель для разбора еды. Нужна поддержка structured JSON и желательно vision. |
| `LLM_RECOMMENDATION_MODEL` | да | Модель для текстовых рекомендаций. |
| `LLM_TIMEOUT_SECONDS` | нет | Timeout одного запроса к ИИ. |
| `LLM_MAX_RETRIES` | нет | Количество ретраев после первой попытки. `1` = максимум 2 попытки. |

Legacy имена `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` тоже могут читаться, но новые имена проекта — `LLM_*`.

## CORS

Один origin:

```env
CORS_ORIGINS=http://localhost:3000
```

Несколько origin-ов:

```env
CORS_ORIGINS=http://localhost:3000,https://app.example.com
```

Для локального MVP можно:

```env
CORS_ORIGINS=*
```
