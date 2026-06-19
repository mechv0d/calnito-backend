# Meals API

## Meal types

| Value | RU label | Автоматически назначается? |
|---|---|---:|
| `breakfast` | завтрак | да |
| `second_breakfast` | второй завтрак | да |
| `lunch` | обед | да |
| `afternoon_snack` | полдник | да |
| `dinner` | ужин | да |
| `snacks` | снеки | нет, вручную |

Автоназначение по локальному времени пользователя:

| Локальное время | Тип |
|---|---|
| `05:00–10:29` | `breakfast` |
| `10:30–11:59` | `second_breakfast` |
| `12:00–15:29` | `lunch` |
| `15:30–17:29` | `afternoon_snack` |
| `17:30–04:59` | `dinner` |

Много приемов одного типа в день разрешено. Много снеков тоже разрешено.

---

## POST `/v1/meals`

Создать прием пищи из текста и необязательного фото.

Backend:

1. проверяет Firebase token;
2. определяет локальное время пользователя;
3. автоназначает `meal_type`;
4. берет последние продукты пользователя для скрытого LLM context;
5. обрабатывает фото, если оно есть;
6. отправляет описание + фото + context в ИИ;
7. валидирует structured JSON;
8. считает калории;
9. сохраняет запись в Firestore;
10. возвращает прием пищи с signed URL для фото.

### Headers

```http
Authorization: Bearer <firebase_id_token>
X-Timezone: Europe/Helsinki
Content-Type: multipart/form-data
```

### Form fields

| Field | Type | Required | Описание |
|---|---|---:|---|
| `description` | string | да | Текст пользователя: что он съел. 1–2000 символов. |
| `photo` | file | нет | `image/jpeg`, `image/png` или `image/webp`. |

### Request без фото

```bash
curl -X POST http://localhost:8000/v1/meals \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timezone: Europe/Helsinki" \
  -F "description=омлет из двух яиц, хлеб и кофе с молоком"
```

### Request с фото

```bash
curl -X POST http://localhost:8000/v1/meals \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timezone: Europe/Helsinki" \
  -F "description=куриная грудка, рис и салат" \
  -F "photo=@./meal.jpg"
```

### Response `201`

```json
{
  "id": "7f4a3e2d7e2a4d79a3ff4b78d8d20a11",
  "meal_type": "lunch",
  "meal_type_label": "обед",
  "date_local": "2026-06-19",
  "consumed_at": "2026-06-19T10:15:00Z",
  "created_at": "2026-06-19T10:15:00Z",
  "updated_at": "2026-06-19T10:15:00Z",
  "description": "куриная грудка, рис и салат",
  "items": [
    {
      "product_name": "куриная грудка",
      "portion_g": 160,
      "kcal_per_100g": 165,
      "confidence": 0.78,
      "calories": 264
    },
    {
      "product_name": "рис вареный",
      "portion_g": 180,
      "kcal_per_100g": 130,
      "confidence": 0.75,
      "calories": 234
    }
  ],
  "totals": {
    "calories": 498,
    "products_count": 2,
    "total_weight_g": 340
  },
  "photo": {
    "storage_path": "users/firebase_uid_123/meals/7f4a3e2d7e2a4d79a3ff4b78d8d20a11/abc.webp",
    "signed_url": "https://your-project.supabase.co/storage/v1/object/sign/meal-photos/...?token=...",
    "width": 1200,
    "height": 900
  }
}
```

### AI failure `503`

Если ИИ timeout, вернул невалидный JSON или все ретраи закончились:

```json
{
  "detail": "Мы проебались, Босс."
}
```

Запись в Firestore в этом случае не создается. Если фото уже успело загрузиться в Supabase, backend пытается удалить orphan-файл.

### Ошибки upload-а

Unsupported content type:

```json
{
  "detail": "Unsupported image type"
}
```

Слишком большой файл:

```json
{
  "detail": "Image is too large"
}
```

Битый image-файл:

```json
{
  "detail": "Invalid image"
}
```

---

## GET `/v1/meals`

Получить приемы пищи за диапазон локальных дат.

### Query params

| Param | Required | Example |
|---|---:|---|
| `from` | да | `2026-06-01` |
| `to` | да | `2026-06-19` |

Внимание: параметры называются именно `from` и `to`.

### Request

```bash
curl "http://localhost:8000/v1/meals?from=2026-06-01&to=2026-06-19" \
  -H "Authorization: Bearer $TOKEN"
```

### Response `200`

```json
{
  "date_from": "2026-06-01",
  "date_to": "2026-06-19",
  "meals": [
    {
      "id": "meal_1",
      "meal_type": "breakfast",
      "meal_type_label": "завтрак",
      "date_local": "2026-06-19",
      "consumed_at": "2026-06-19T06:20:00Z",
      "created_at": "2026-06-19T06:20:00Z",
      "updated_at": "2026-06-19T06:20:00Z",
      "description": "овсянка с бананом",
      "items": [],
      "totals": {
        "calories": 380,
        "products_count": 2,
        "total_weight_g": 280
      },
      "photo": null
    }
  ],
  "total_calories": 380
}
```

---

## GET `/v1/meals/today`

Сводка за сегодняшнюю локальную дату пользователя.

### Headers

```http
Authorization: Bearer <firebase_id_token>
X-Timezone: Europe/Helsinki
```

### Request

```bash
curl http://localhost:8000/v1/meals/today \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timezone: Europe/Helsinki"
```

### Response `200`

```json
{
  "date": "2026-06-19",
  "total_calories": 1450.5,
  "by_meal_type": {
    "breakfast": 380,
    "second_breakfast": 0,
    "lunch": 620.5,
    "afternoon_snack": 0,
    "dinner": 0,
    "snacks": 450
  },
  "meals_count": 3,
  "meals": []
}
```

---

## GET `/v1/meals/summary/today`

Алиас для `/v1/meals/today`.

Используй его, если frontend уже завязан на путь `/summary/today`.

---

## GET `/v1/meals/by-day`

Получить приемы пищи за конкретную локальную дату.

### Query params

| Param | Required | Example |
|---|---:|---|
| `date` | да | `2026-06-19` |

### Request

```bash
curl "http://localhost:8000/v1/meals/by-day?date=2026-06-19" \
  -H "Authorization: Bearer $TOKEN"
```

### Response `200`

```json
{
  "date": "2026-06-19",
  "meals": [],
  "total_calories": 0
}
```

---

## GET `/v1/meals/{meal_id}`

Получить один прием пищи.

### Request

```bash
curl http://localhost:8000/v1/meals/7f4a3e2d7e2a4d79a3ff4b78d8d20a11 \
  -H "Authorization: Bearer $TOKEN"
```

### Response `200`

Возвращает `MealResponse`.

### Ошибка `404`

```json
{
  "detail": "Meal not found"
}
```

---

## PATCH `/v1/meals/{meal_id}`

Ручная правка приема пищи.

Можно менять:

- `description`;
- `meal_type`;
- `items`;
- `consumed_at`, но только если итоговый `meal_type` — `snacks`.

### Body: изменить тип

```json
{
  "meal_type": "snacks"
}
```

### Body: изменить описание

```json
{
  "description": "омлет, хлеб, кофе с молоком"
}
```

### Body: ручная правка продуктов

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

Backend пересчитает `calories`, `products_count`, `total_weight_g` и поставит `manual_edited=true` внутри Firestore документа.

### Body: снек с ручным временем

```json
{
  "meal_type": "snacks",
  "consumed_at": "2026-06-19T21:30:00+03:00"
}
```

`consumed_at` обязан включать timezone offset.

### Request

```bash
curl -X PATCH http://localhost:8000/v1/meals/$MEAL_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timezone: Europe/Helsinki" \
  -H "Content-Type: application/json" \
  -d '{"meal_type":"snacks","consumed_at":"2026-06-19T21:30:00+03:00"}'
```

### Ошибка при смене времени не-снека

```json
{
  "detail": "Manual consumed_at change is allowed only for snacks"
}
```

HTTP status: `400`.

---

## DELETE `/v1/meals/{meal_id}`

Удалить прием пищи. Если у него было фото, backend также удалит файл из Supabase Storage.

### Request

```bash
curl -X DELETE http://localhost:8000/v1/meals/$MEAL_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Response `200`

```json
{
  "ok": true,
  "deleted_id": "7f4a3e2d7e2a4d79a3ff4b78d8d20a11"
}
```

### Ошибка `404`

```json
{
  "detail": "Meal not found"
}
```
