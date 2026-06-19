# Авторизация

Все endpoint-ы `/v1/*`, кроме `/health`, требуют Firebase ID token.

## Header

```http
Authorization: Bearer <firebase_id_token>
```

Опционально, но очень желательно:

```http
X-Timezone: Europe/Helsinki
```

## Как backend использует token

1. Frontend логинит пользователя через Firebase Auth.
2. Frontend получает ID token.
3. Frontend отправляет token в `Authorization`.
4. Backend проверяет token через Firebase Admin SDK.
5. Backend достает `uid` и использует его как owner данных.

`uid` нельзя передавать в body или query. Он игнорируется архитектурно.

## Пример headers

```http
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6...
X-Timezone: Europe/Helsinki
```

## Ошибки авторизации

### Нет токена

```json
{
  "detail": "Missing Firebase bearer token"
}
```

HTTP status: `401`.

### Невалидный токен

```json
{
  "detail": "Invalid Firebase token"
}
```

HTTP status: `401`.
