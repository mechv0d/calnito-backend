# Endpoints overview

Base URL локально:

```text
http://localhost:8000
```

API prefix:

```text
/v1
```

## Таблица endpoint-ов

| Method | Path | Auth | Назначение |
|---|---|---:|---|
| `GET` | `/health` | нет | Healthcheck backend-а. |
| `GET` | `/v1/users/me` | да | Получить или создать профиль текущего пользователя. |
| `PATCH` | `/v1/users/me` | да | Обновить timezone пользователя. |
| `POST` | `/v1/meals` | да | Создать прием пищи из текста и необязательного фото. |
| `GET` | `/v1/meals?from=YYYY-MM-DD&to=YYYY-MM-DD` | да | Получить приемы пищи за диапазон локальных дат. |
| `GET` | `/v1/meals/today` | да | Сводка за сегодня + сегодняшние приемы. |
| `GET` | `/v1/meals/summary/today` | да | Алиас для `/v1/meals/today`. |
| `GET` | `/v1/meals/by-day?date=YYYY-MM-DD` | да | Приемы пищи за конкретный день. |
| `GET` | `/v1/meals/{meal_id}` | да | Получить один прием пищи. |
| `PATCH` | `/v1/meals/{meal_id}` | да | Ручная правка приема пищи. |
| `DELETE` | `/v1/meals/{meal_id}` | да | Удалить прием пищи и его фото. |
| `GET` | `/v1/stats?from=YYYY-MM-DD&to=YYYY-MM-DD` | да | Статистика за диапазон локальных дат. |
| `POST` | `/v1/recommendations` | да | Рекомендации по питанию за последние 30 дней. |

## Общие headers

```http
Authorization: Bearer <firebase_id_token>
X-Timezone: Europe/Helsinki
```

`X-Timezone` используется для:

- определения сегодняшней локальной даты;
- автоматического типа приема пищи при создании;
- пересчета `date_local` при ручной правке времени снеков;
- периода рекомендаций за 30 дней.

Если `X-Timezone` не передан, backend использует `DEFAULT_TIMEZONE` из `.env`.

## Формат дат

Локальная дата:

```text
YYYY-MM-DD
```

Пример:

```text
2026-06-19
```

Datetime с timezone:

```text
2026-06-19T21:30:00+03:00
```
