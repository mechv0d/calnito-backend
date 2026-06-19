# Curl examples

Перед примерами:

```bash
export API_URL="http://localhost:8000"
export TOKEN="PASTE_FIREBASE_ID_TOKEN_HERE"
export TZ_NAME="Europe/Helsinki"
```

PowerShell:

```powershell
$env:API_URL="http://localhost:8000"
$env:TOKEN="PASTE_FIREBASE_ID_TOKEN_HERE"
$env:TZ_NAME="Europe/Helsinki"
```

## Healthcheck

```bash
curl "$API_URL/health"
```

## Get me

```bash
curl "$API_URL/v1/users/me" \
  -H "Authorization: Bearer $TOKEN"
```

## Update timezone

```bash
curl -X PATCH "$API_URL/v1/users/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"timezone":"Europe/Helsinki"}'
```

## Create meal without photo

```bash
curl -X POST "$API_URL/v1/meals" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timezone: $TZ_NAME" \
  -F "description=омлет из двух яиц, хлеб и кофе с молоком"
```

## Create meal with photo

```bash
curl -X POST "$API_URL/v1/meals" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timezone: $TZ_NAME" \
  -F "description=куриная грудка, рис и салат" \
  -F "photo=@./meal.jpg"
```

## Today summary

```bash
curl "$API_URL/v1/meals/today" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timezone: $TZ_NAME"
```

## Meals by day

```bash
curl "$API_URL/v1/meals/by-day?date=2026-06-19" \
  -H "Authorization: Bearer $TOKEN"
```

## Meals range

```bash
curl "$API_URL/v1/meals?from=2026-06-01&to=2026-06-19" \
  -H "Authorization: Bearer $TOKEN"
```

## One meal

```bash
curl "$API_URL/v1/meals/$MEAL_ID" \
  -H "Authorization: Bearer $TOKEN"
```

## Change meal type to snacks

```bash
curl -X PATCH "$API_URL/v1/meals/$MEAL_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"meal_type":"snacks"}'
```

## Change snack time

```bash
curl -X PATCH "$API_URL/v1/meals/$MEAL_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timezone: $TZ_NAME" \
  -H "Content-Type: application/json" \
  -d '{"meal_type":"snacks","consumed_at":"2026-06-19T21:30:00+03:00"}'
```

## Manual edit products

```bash
curl -X PATCH "$API_URL/v1/meals/$MEAL_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

## Delete meal

```bash
curl -X DELETE "$API_URL/v1/meals/$MEAL_ID" \
  -H "Authorization: Bearer $TOKEN"
```

## Stats

```bash
curl "$API_URL/v1/stats?from=2026-06-01&to=2026-06-19" \
  -H "Authorization: Bearer $TOKEN"
```

## Recommendations

```bash
curl -X POST "$API_URL/v1/recommendations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timezone: $TZ_NAME"
```
