# Calnito / Food AI Backend — API Docs

Документация для MVP backend на FastAPI.

Базовый URL для локального запуска:

```text
http://localhost:8000
```

API prefix:

```text
/v1
```

## Быстрая навигация

| Раздел | Файл |
|---|---|
| Быстрый старт | [`quickstart.md`](./quickstart.md) |
| Переменные окружения | [`env.md`](./env.md) |
| Авторизация | [`auth.md`](./auth.md) |
| Общая таблица endpoint-ов | [`endpoints/00-overview.md`](./endpoints/00-overview.md) |
| Профиль пользователя | [`endpoints/users.md`](./endpoints/users.md) |
| Приемы пищи | [`endpoints/meals.md`](./endpoints/meals.md) |
| Статистика | [`endpoints/stats.md`](./endpoints/stats.md) |
| Рекомендации | [`endpoints/recommendations.md`](./endpoints/recommendations.md) |
| Healthcheck | [`endpoints/health.md`](./endpoints/health.md) |
| JSON-схемы ответов | [`schemas.md`](./schemas.md) |
| Ошибки API | [`errors.md`](./errors.md) |
| Фото и signed URLs | [`photos-and-storage.md`](./photos-and-storage.md) |
| Frontend flow | [`frontend/frontend-flow.md`](./frontend/frontend-flow.md) |
| Готовые curl-примеры | [`examples/curl.md`](./examples/curl.md) |
| REST Client файл | [`examples/api.http`](./examples/api.http) |
| Firestore структура | [`firestore.md`](./firestore.md) |
| Troubleshooting | [`ops/troubleshooting.md`](./ops/troubleshooting.md) |

## Главные правила API

1. Почти все `/v1/*` endpoint-ы требуют Firebase token:

```http
Authorization: Bearer <firebase_id_token>
```

2. Для корректной локальной даты и авто-типа приема пищи передавай timezone:

```http
X-Timezone: Europe/Helsinki
```

3. `uid` никогда не передается с фронта. Backend берет его из Firebase token.

4. Фото хранятся в private Supabase Storage bucket. В ответах API приходит короткоживущий `signed_url`.

5. Если ИИ не смог распарсить еду после всех ретраев, backend возвращает честную ошибку:

```json
{
  "detail": "Мы проебались, Босс."
}
```

HTTP status: `503`.
