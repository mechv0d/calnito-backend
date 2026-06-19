# Ошибки API

## Общий формат FastAPI ошибки

```json
{
  "detail": "error message"
}
```

Для validation errors FastAPI возвращает массив объектов:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "description"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

## Таблица ошибок

| HTTP | Detail | Где возникает |
|---:|---|---|
| `400` | `Invalid timezone` | Невалидный `X-Timezone` или timezone профиля. |
| `400` | `Unsupported image type` | Фото не `jpeg/png/webp`. |
| `400` | `Image is too large` | Файл больше `MAX_UPLOAD_BYTES`. |
| `400` | `Invalid image` | Файл не удалось открыть как изображение. |
| `400` | `Manual consumed_at change is allowed only for snacks` | Попытка поменять время не-снека. |
| `401` | `Missing Firebase bearer token` | Нет `Authorization: Bearer ...`. |
| `401` | `Invalid Firebase token` | Firebase token не прошел проверку. |
| `404` | `Meal not found` | Прием пищи не найден или не принадлежит пользователю. |
| `422` | validation error | Невалидный body/query/form. |
| `503` | `Мы проебались, Босс.` | ИИ не ответил валидно после всех попыток. |

## AI failure

Endpoint-ы, которые могут вернуть AI failure:

- `POST /v1/meals`
- `POST /v1/recommendations`

Ответ:

```json
{
  "detail": "Мы проебались, Босс."
}
```

Status:

```text
503 Service Unavailable
```

Для `POST /v1/meals` запись в Firestore не создается.

## Validation примеры

### `consumed_at` без timezone

Request:

```json
{
  "meal_type": "snacks",
  "consumed_at": "2026-06-19T21:30:00"
}
```

Response `422`:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "consumed_at"],
      "msg": "Value error, consumed_at must include timezone"
    }
  ]
}
```

### Пустой список `items`

```json
{
  "items": []
}
```

Response `422`, потому что `items` должен содержать минимум 1 продукт.
