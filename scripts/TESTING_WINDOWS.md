# Unit tests на Windows

## Первый запуск

Из корня проекта:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\run_tests_windows.ps1
```

Или вручную:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m pytest
```

## Важно

Запускай именно так:

```powershell
python -m pytest
```

А не просто `pytest`, чтобы Windows точно использовал Python из активного `.venv`.

## Что мокается

Unit tests не ходят в реальные сервисы:

- Firebase Auth;
- Firestore;
- Supabase Storage;
- LLM/OpenAI-compatible provider.

Тестовые `.env` значения выставляются автоматически в `tests/conftest.py`.

## Что покрыто

- автоопределение типа приема пищи по времени;
- расчет калорий и totals;
- нормализация продуктов;
- скрытый контекст последних продуктов;
- обработка фото в WebP;
- signed URL logic;
- сериализация meal response;
- Firebase auth dependency;
- AI client retries и ошибка после exhausted retries;
- создание приема пищи;
- честная ошибка `Мы проебались, Босс.`;
- ручная правка продуктов;
- ручная смена времени только для snacks;
- удаление фото при delete;
- today summary;
- stats;
- recommendations;
- users profile;
- smoke tests всех API роутов через FastAPI TestClient.
