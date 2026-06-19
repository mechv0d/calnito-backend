# Unit tests для Food MVP Backend

Архив содержит:

- `tests/` — unit tests;
- `pytest.ini`;
- `requirements-dev.txt`;
- `scripts/run_tests_windows.ps1`;
- `TESTING_WINDOWS.md`;

## Важный фикс перед запуском

В текущей версии проекта есть опечатка:

```python
self.settings.openai_model
```

Нужно заменить на:

```python
self.settings.llm_model
```

Файл:

```text
app/meals/service.py
```

Иначе тест создания приема пищи правильно упадет.

## Запуск Windows

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\run_tests_windows.ps1
```

Или:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m pytest
```
