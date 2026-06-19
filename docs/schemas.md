# JSON-схемы API

## MealResponse

```json
{
  "id": "string",
  "meal_type": "breakfast | second_breakfast | lunch | afternoon_snack | dinner | snacks",
  "meal_type_label": "string",
  "date_local": "YYYY-MM-DD",
  "consumed_at": "ISO datetime",
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime",
  "description": "string",
  "items": [
    {
      "product_name": "string",
      "portion_g": 180,
      "kcal_per_100g": 154,
      "confidence": 1,
      "calories": 277.2
    }
  ],
  "totals": {
    "calories": 277.2,
    "products_count": 1,
    "total_weight_g": 180
  },
  "photo": {
    "storage_path": "string | null",
    "signed_url": "string | null",
    "width": 1200,
    "height": 900
  }
}
```

`photo` может быть `null`, если прием пищи был создан без фото.

## MealItem

| Field | Type | Limits | Описание |
|---|---|---|---|
| `product_name` | string | 1–120 chars | Название продукта. |
| `portion_g` | number | `> 0`, `<= 5000` | Вес порции в граммах. |
| `kcal_per_100g` | number | `>= 0`, `<= 1000` | Калорийность на 100 г. |
| `confidence` | number | `0..1` | Уверенность оценки. |
| `calories` | number | `>= 0` | `portion_g * kcal_per_100g / 100`. |

## MealUpdateRequest

```json
{
  "description": "string | optional",
  "meal_type": "breakfast | second_breakfast | lunch | afternoon_snack | dinner | snacks | optional",
  "consumed_at": "ISO datetime with timezone | optional",
  "items": [
    {
      "product_name": "омлет",
      "portion_g": 180,
      "kcal_per_100g": 154,
      "confidence": 1
    }
  ]
}
```

Правила:

- `items` должен содержать 1–20 продуктов, если передан.
- `consumed_at` обязан содержать timezone offset.
- `consumed_at` можно менять только для `snacks`.
- Если меняешь `items`, backend сам пересчитывает калории.

## TodaySummaryResponse

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

## DayMealsResponse

```json
{
  "date": "2026-06-19",
  "meals": [],
  "total_calories": 0
}
```

## MealsRangeResponse

```json
{
  "date_from": "2026-06-01",
  "date_to": "2026-06-19",
  "meals": [],
  "total_calories": 0
}
```

## StatsResponse

```json
{
  "period": {
    "date_from": "2026-06-01",
    "date_to": "2026-06-19"
  },
  "totals": {
    "calories": 0,
    "meals_count": 0,
    "days_count": 0,
    "products_count": 0
  },
  "averages": {
    "calories_per_day": 0,
    "calories_per_meal": 0,
    "products_per_meal": 0,
    "weight_per_meal_g": 0
  },
  "calories_by_day": {},
  "calories_by_meal_type": {},
  "top_products_by_frequency": [],
  "top_products_by_calories": []
}
```

## RecommendationResponse

```json
{
  "text": "string",
  "meals_analyzed": 18,
  "period": {
    "from": "2026-06-13",
    "to": "2026-06-19"
  }
}
```
