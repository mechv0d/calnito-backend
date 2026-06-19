# Healthcheck

## GET `/health`

Проверяет, что FastAPI app запустился.

Auth не нужен.

### Request

```bash
curl http://localhost:8000/health
```

### Response `200`

```json
{
  "status": "ok"
}
```
