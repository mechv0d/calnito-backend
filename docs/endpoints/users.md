# Users API

## GET `/v1/users/me`

Получить профиль текущего пользователя. Если документа `users/{uid}` еще нет, backend создаст его.

### Headers

```http
Authorization: Bearer <firebase_id_token>
```

### Request

```bash
curl http://localhost:8000/v1/users/me \
  -H "Authorization: Bearer $TOKEN"
```

### Response `200`

```json
{
  "uid": "firebase_uid_123",
  "email": "boss@example.com",
  "timezone": "Europe/Helsinki",
  "created_at": "2026-06-19T08:00:00Z",
  "updated_at": "2026-06-19T08:10:00Z"
}
```

Если timezone еще не задан:

```json
{
  "uid": "firebase_uid_123",
  "email": "boss@example.com",
  "timezone": null,
  "created_at": "2026-06-19T08:00:00Z",
  "updated_at": "2026-06-19T08:00:00Z"
}
```

---

## PATCH `/v1/users/me`

Обновить timezone пользователя.

### Headers

```http
Authorization: Bearer <firebase_id_token>
Content-Type: application/json
```

### Body

```json
{
  "timezone": "Europe/Helsinki"
}
```

### Request

```bash
curl -X PATCH http://localhost:8000/v1/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"timezone":"Europe/Helsinki"}'
```

### Response `200`

```json
{
  "uid": "firebase_uid_123",
  "email": "boss@example.com",
  "timezone": "Europe/Helsinki",
  "created_at": "2026-06-19T08:00:00Z",
  "updated_at": "2026-06-19T08:15:00Z"
}
```

### Ошибка `400`

```json
{
  "detail": "Invalid timezone"
}
```
