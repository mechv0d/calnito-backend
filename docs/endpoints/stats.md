# Stats API

## GET `/v1/stats`

Статистика за диапазон локальных дат.

### Query params

| Param | Required | Example |
|---|---:|---|
| `from` | да | `2026-06-01` |
| `to` | да | `2026-06-19` |

Внимание: в текущем коде параметры называются именно `from` и `to`, не `date_from` и `date_to`.

### Headers

```http
Authorization: Bearer <firebase_id_token>
```

### Request

```bash
curl "http://localhost:8000/v1/stats?from=2026-06-01&to=2026-06-19" \
  -H "Authorization: Bearer $TOKEN"
```

### Response `200`

```json
{
  "period": {
    "date_from": "2026-06-01",
    "date_to": "2026-06-19"
  },
  "totals": {
    "calories": 12450.5,
    "meals_count": 28,
    "days_count": 14,
    "products_count": 76
  },
  "averages": {
    "calories_per_day": 889.3,
    "calories_per_meal": 444.7,
    "products_per_meal": 2.7,
    "weight_per_meal_g": 315.2
  },
  "calories_by_day": {
    "2026-06-01": 1650,
    "2026-06-02": 1420.5
  },
  "calories_by_meal_type": {
    "breakfast": 2500,
    "second_breakfast": 600,
    "lunch": 4300,
    "afternoon_snack": 800,
    "dinner": 3500.5,
    "snacks": 750
  },
  "top_products_by_frequency": [
    ["кофе с молоком", 8],
    ["овсянка", 5]
  ],
  "top_products_by_calories": [
    {
      "product_name": "рис вареный",
      "calories": 1250
    },
    {
      "product_name": "куриная грудка",
      "calories": 990
    }
  ]
}
```

## Метрики

| Поле | Значение |
|---|---|
| `totals.calories` | Сумма калорий за период. |
| `totals.meals_count` | Количество приемов пищи. |
| `totals.days_count` | Количество дней, где были записи. |
| `totals.products_count` | Суммарное количество item-ов во всех приемах. |
| `averages.calories_per_day` | Средние калории на день с записями. |
| `averages.calories_per_meal` | Средние калории на прием пищи. |
| `averages.products_per_meal` | Среднее количество продуктов на прием пищи. |
| `averages.weight_per_meal_g` | Средний вес приема пищи в граммах. |
| `calories_by_day` | Калории по локальным датам. |
| `calories_by_meal_type` | Калории по типам приемов. |
| `top_products_by_frequency` | Топ продуктов по частоте. |
| `top_products_by_calories` | Топ продуктов по суммарным калориям. |
