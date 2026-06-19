# Troubleshooting

## Windows: `Fatal error in launcher: Unable to create process... cosita\.venv ... calnito\.venv`

Причина: `.venv` был перенесен/скопирован из другой папки. Windows launcher внутри `uvicorn.exe` запомнил старый абсолютный путь к Python.

Решение из папки проекта:

```powershell
deactivate
Remove-Item -Recurse -Force .venv
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Проверка:

```powershell
python -c "import sys; print(sys.executable)"
where.exe python
where.exe uvicorn
```

Путь должен быть внутри текущего проекта.

## `ModuleNotFoundError`

Убедись, что запускаешь из корня проекта:

```bash
python -m uvicorn app.main:app --reload
```

Не запускай из папки `app/`.

## `ValidationError: Set SUPABASE_SECRET_KEY`

В `.env` нет server-side ключа Supabase.

Нужно:

```env
SUPABASE_SECRET_KEY=sb_secret_...
```

Legacy `SUPABASE_SERVICE_ROLE_KEY` может читаться как fallback, но лучше использовать новый `sb_secret_...`.

## `Invalid Firebase token`

Проверь:

1. Frontend отправляет именно Firebase ID token, не refresh token.
2. Header строго такой:

```http
Authorization: Bearer <token>
```

3. Firebase service account относится к тому же project id.

## `Invalid timezone`

Проверь `X-Timezone`:

```http
X-Timezone: Europe/Helsinki
```

Не используй `GMT+3` как timezone name. Нужен IANA timezone.

## `Manual consumed_at change is allowed only for snacks`

Так задумано. Время можно вручную менять только для снеков.

Сначала сделай прием снеком:

```json
{
  "meal_type": "snacks",
  "consumed_at": "2026-06-19T21:30:00+03:00"
}
```

## `Мы проебались, Босс.`

Это user-facing ошибка AI pipeline.

Возможные причины:

- LLM provider не отвечает;
- timeout;
- неверный `LLM_BASE_URL`;
- неверный `LLM_API_KEY`;
- модель не поддерживает vision;
- модель не поддерживает structured JSON / `response_format`;
- модель вернула невалидный JSON;
- слишком большой prompt или image payload.

Что проверить:

```env
LLM_BASE_URL=https://provider.example/v1
LLM_API_KEY=...
LLM_MODEL=...
LLM_TIMEOUT_SECONDS=45
LLM_MAX_RETRIES=1
```

## Важный known issue в архиве v3

Если в `POST /v1/meals` после успешного ответа LLM падает `AttributeError: 'Settings' object has no attribute 'openai_model'`, поправь в файле:

```text
app/meals/service.py
```

Было:

```python
'model': self.settings.openai_model,
```

Должно быть:

```python
'model': self.settings.llm_model,
```

Это не меняет API docs, но влияет на создание записи после успешного AI parse.
