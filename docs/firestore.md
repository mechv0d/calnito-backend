# Firestore структура

## Collections

```text
users/{uid}
users/{uid}/meals/{meal_id}
```

## User document

```json
{
  "uid": "firebase_uid_123",
  "email": "boss@example.com",
  "timezone": "Europe/Helsinki",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

## Meal document

```json
{
  "id": "7f4a3e2d7e2a4d79a3ff4b78d8d20a11",
  "uid": "firebase_uid_123",
  "description": "куриная грудка, рис и салат",
  "meal_type": "lunch",
  "date_local": "2026-06-19",
  "consumed_at": "timestamp UTC",
  "created_at": "timestamp UTC",
  "updated_at": "timestamp UTC",
  "photo": {
    "storage_path": "users/firebase_uid_123/meals/.../photo.webp",
    "width": 1200,
    "height": 900
  },
  "items": [
    {
      "product_name": "куриная грудка",
      "portion_g": 160,
      "kcal_per_100g": 165,
      "confidence": 0.78,
      "calories": 264
    }
  ],
  "totals": {
    "calories": 264,
    "products_count": 1,
    "total_weight_g": 160
  },
  "llm": {
    "provider": "openai-compatible",
    "model": "your-model",
    "estimated": true,
    "notes": null
  },
  "manual_edited": true
}
```

`manual_edited` появляется после ручной правки `items`.

## Запросы, под которые нужны индексы

Проект использует такие query patterns:

```text
users/{uid}/meals
  where date_local == ...
  order by consumed_at

users/{uid}/meals
  where date_local >= ...
  where date_local <= ...
  order by date_local
  order by consumed_at

users/{uid}/meals
  where meal_type == ...
  order by consumed_at desc

users/{uid}/meals
  where consumed_at >= ...
  order by consumed_at
```

В проекте есть `firestore.indexes.json`. Если Firestore попросит composite index, он обычно отдаст прямую ссылку на создание индекса в Firebase Console.
