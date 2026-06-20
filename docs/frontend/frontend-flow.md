# Frontend flow

## 1. Первый запуск пользователя

1. Frontend логинит пользователя через Firebase Auth.
2. Получает Firebase ID token.
3. Вызывает:

```http
GET /v1/users/me
```

4. Если `timezone` пустой, frontend определяет timezone браузера:

```js
Intl.DateTimeFormat().resolvedOptions().timeZone
```

5. Сохраняет timezone:

```http
PATCH /v1/users/me
```

Body:

```json
{
  "timezone": "Europe/Helsinki"
}
```

## 2. Главный экран

При открытии главного экрана:

```http
GET /v1/meals/today
```

Показать:

- сумму за день: `total_calories`;
- суммы по типам: `by_meal_type`;
- список приемов: `meals`;
- фото через `meal.photo.signed_url`, если есть.

## 3. Создание приема пищи

Пользователь вводит текст и необязательно добавляет фото.

Frontend отправляет:

```http
POST /v1/meals
Content-Type: multipart/form-data
```

Fields:

```text
description = "омлет из двух яиц и кофе с молоком"
photo = optional file
```

После `201` можно:

- сразу добавить response meal в локальный список;
- или перезапросить `/v1/meals/today`.

## 4. AI failure UX

Если response:

```json
{
  "detail": "Мы проебались, Босс."
}
```

Status:

```text
503
```

Frontend показывает именно эту честную ошибку. Dummy данные не подставлять.

## 5. Ручная правка

Открыть экран редактирования приема пищи.

Изменить продукты:

```http
PATCH /v1/meals/{meal_id}
```

Body:

```json
{
  "items": [
    {
      "product_name": "омлет",
      "portion_g": 180,
      "kcal_per_100g": 154,
      "confidence": 1
    }
  ]
}
```

Backend вернет пересчитанный meal.

## 6. Снеки

Чтобы сделать прием снеком:

```json
{
  "meal_type": "snacks"
}
```

Чтобы сделать снек и выставить время:

```json
{
  "meal_type": "snacks",
  "consumed_at": "2026-06-19T21:30:00+03:00"
}
```

Для не-снеков `consumed_at` менять нельзя.

## 7. Страница просмотра по дням

Выбран день в календаре:

```http
GET /v1/meals/by-day?date=2026-06-19
```

## 8. Статистика

Выбран период:

```http
GET /v1/stats?from=2026-06-01&to=2026-06-19
```

## 9. Рекомендации

Кнопка “Показать рекомендации”:

```http
POST /v1/recommendations
```

Backend сам берет последние 30 дней.
