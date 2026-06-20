# Recommendations API

## POST `/v1/recommendations`

Сгенерировать рекомендации по питанию за последние 30 локальных дней.

Backend:

1. определяет текущую локальную дату пользователя по `X-Timezone`;
2. берет период `сегодня - 29 дней` → `сегодня`;
3. достает приемы пищи из Firestore;
4. отправляет отдельный prompt в LLM;
5. возвращает текстовую рекомендацию.

### Headers

```http
Authorization: Bearer <firebase_id_token>
X-Timezone: Europe/Helsinki
```

### Request

```bash
curl -X POST http://localhost:8000/v1/recommendations \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timezone: Europe/Helsinki"
```

### Response `200`

```json
{
  "text": "За последние 30 дней видно, что обеды самые калорийные...",
  "meals_analyzed": 18,
  "period": {
    "from": "2026-05-21",
    "to": "2026-06-19"
  }
}
```

### Если данных нет

```json
{
  "text": "Пока недостаточно данных для рекомендаций. Добавьте несколько приемов пищи.",
  "meals_analyzed": 0,
  "period": {
    "from": "2026-05-21",
    "to": "2026-06-19"
  }
}
```

### AI failure `503`

```json
{
  "detail": "Мы проебались, Босс."
}
```
