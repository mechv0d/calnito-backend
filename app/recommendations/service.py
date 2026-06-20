from collections import defaultdict
from datetime import timedelta

from app.common.enums import MealType
from app.common.http import ai_failed_exception
from app.common.time import get_zoneinfo, now_utc
from app.llm.client import AIClient
from app.llm.exceptions import AIExhaustedError
from app.meals.repository import MealRepository


RECOMMENDATION_DAYS = 30


class RecommendationService:
    def __init__(self) -> None:
        self.repo = MealRepository()
        self.ai = AIClient()

    def weekly_recommendations(self, uid: str, timezone_name: str | None) -> dict:
        try:
            tz = get_zoneinfo(timezone_name)
        except ValueError as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail='Invalid timezone') from exc

        today = now_utc().astimezone(tz).date()
        start = today - timedelta(days=RECOMMENDATION_DAYS - 1)

        meals = self.repo.list_between_days(uid, start.isoformat(), today.isoformat())
        if not meals:
            return {
                'text': 'Пока недостаточно данных для рекомендаций. Добавьте несколько приемов пищи.',
                'meals_analyzed': 0,
                'period': {
                    'from': start.isoformat(),
                    'to': today.isoformat(),
                },
            }

        try:
            text = self.ai.generate_recommendations(
                build_recommendation_payload(
                    meals=meals,
                    date_from=start.isoformat(),
                    date_to=today.isoformat(),
                )
            )
        except AIExhaustedError as exc:
            raise ai_failed_exception() from exc

        return {
            'text': text,
            'meals_analyzed': len(meals),
            'period': {
                'from': start.isoformat(),
                'to': today.isoformat(),
            },
        }


def build_recommendation_payload(meals: list[dict], date_from: str, date_to: str) -> dict:
    calories_by_day: dict[str, float] = defaultdict(float)
    calories_by_type: dict[str, float] = {meal_type.value: 0.0 for meal_type in MealType}
    product_calories: dict[str, float] = defaultdict(float)
    product_portions: dict[str, float] = defaultdict(float)
    product_kcal_per_100g_sum: dict[str, float] = defaultdict(float)

    compact_meals = []
    total_calories = 0.0

    for meal in meals:
        meal_calories = float((meal.get('totals') or {}).get('calories', 0))
        meal_type = meal.get('meal_type')
        date_local = meal.get('date_local')

        total_calories += meal_calories
        if date_local:
            calories_by_day[str(date_local)] += meal_calories
        if meal_type:
            calories_by_type[str(meal_type)] = calories_by_type.get(str(meal_type), 0.0) + meal_calories

        compact_items = []
        for item in meal.get('items', []):
            name = str(item.get('product_name', '')).strip().lower()
            if not name:
                continue

            portion_g = _float_or_zero(item.get('portion_g'))
            calories = _float_or_zero(item.get('calories'))
            kcal_per_100g = _resolve_kcal_per_100g(item, calories, portion_g)

            product_calories[name] += calories
            product_portions[name] += portion_g
            if kcal_per_100g is not None and portion_g > 0:
                product_kcal_per_100g_sum[name] += kcal_per_100g * portion_g

            compact_items.append({
                'product_name': name,
                'portion_g': round(portion_g, 1),
                'calories': round(calories, 1),
                'kcal_per_100g': round(kcal_per_100g, 1) if kcal_per_100g is not None else None,
            })

        compact_meals.append({
            'date_local': date_local,
            'meal_type': meal_type,
            'description': meal.get('description'),
            'total_calories': round(meal_calories, 1),
            'items': compact_items,
        })

    days_with_entries = len(calories_by_day)
    meals_count = len(meals)

    return {
        'task': 'nutrition_recommendations',
        'language': 'ru',
        'data_quality': {
            'period_days': RECOMMENDATION_DAYS,
            'days_with_entries': days_with_entries,
            'meals_count': meals_count,
        },
        'summary': {
            'total_logged_calories': round(total_calories, 1),
            'average_logged_calories_per_day_with_entries': round(total_calories / days_with_entries, 1) if days_with_entries else 0,
            'average_logged_calories_per_meal': round(total_calories / meals_count, 1) if meals_count else 0,
        },
        'calories_by_day': {
            day: round(calories, 1)
            for day, calories in sorted(calories_by_day.items())
        },
        'calories_by_meal_type': {
            meal_type: round(calories, 1)
            for meal_type, calories in calories_by_type.items()
        },
        'top_products_by_calories': _top_products_by_calories(
            product_calories,
            product_portions,
            product_kcal_per_100g_sum,
        ),
        'meals': compact_meals,
    }


def _float_or_zero(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _resolve_kcal_per_100g(item: dict, calories: float, portion_g: float) -> float | None:
    value = item.get('kcal_per_100g')
    if value is not None:
        return _float_or_zero(value)
    if calories > 0 and portion_g > 0:
        return calories / portion_g * 100
    return None


def _top_products_by_calories(
    product_calories: dict[str, float],
    product_portions: dict[str, float],
    product_kcal_per_100g_sum: dict[str, float],
) -> list[dict]:
    products = []
    for name, calories in product_calories.items():
        portion_g = product_portions.get(name, 0.0)
        if portion_g > 0 and product_kcal_per_100g_sum.get(name):
            kcal_per_100g = product_kcal_per_100g_sum[name] / portion_g
        elif portion_g > 0:
            kcal_per_100g = calories / portion_g * 100
        else:
            kcal_per_100g = None

        products.append({
            'product_name': name,
            'calories': round(calories, 1),
            'kcal_per_100g': round(kcal_per_100g, 1) if kcal_per_100g is not None else None,
        })

    return sorted(products, key=lambda product: product['calories'], reverse=True)[:10]
