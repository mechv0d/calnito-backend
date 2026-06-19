# Быстрый старт

## 1. Установить зависимости

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Создать `.env`

```bash
cp .env.example .env
```

Заполни значения по [`env.md`](./env.md).

## 3. Запустить backend

Рекомендуемый способ:

```bash
python -m uvicorn app.main:app --reload
```

На Windows лучше запускать именно через `python -m`, чтобы не поймать старый launcher от перенесенного `.venv`.

## 4. Проверить healthcheck

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{
  "status": "ok"
}
```

## 5. Проверить Swagger UI

Открой:

```text
http://localhost:8000/docs
```

FastAPI сам генерирует Swagger UI из роутеров проекта.

## 6. Проверить API через готовый REST Client файл

Открой [`examples/api.http`](./examples/api.http), подставь токен и запускай запросы из VS Code REST Client или JetBrains HTTP Client.
