from collections import defaultdict
from datetime import datetime, time, timedelta

from fastapi import HTTPException

from app.common.enums import MEAL_TYPE_LABELS_RU, MealType
from app.common.http import ai_failed_exception
from app.common.time import get_zoneinfo, now_utc
from app.llm.client import AIClient
from app.llm.exceptions import AIExhaustedError
from app.meals.repository import MealRepository
from app.recommendations.usage import RecommendationLimiter


RECOMMENDATION_DAYS = 30


class RecommendationService:
    def __init__(self) -> None:
        self.repo = MealRepository()
        self.ai = AIClient()
        self.limiter = RecommendationLimiter()

    def limits(self, uid: str, timezone_name: str | None) -> dict:
        tz = self._resolve_tz(timezone_name)
        today = now_utc().astimezone(tz).date()
        return self.limiter.status(uid, today).to_dict()

    def weekly_recommendations(self, uid: str, timezone_name: str | None) -> dict:
        tz = self._resolve_tz(timezone_name)
        local_today = now_utc().astimezone(tz).date()
        limit_before = self.limiter.ensure_available(uid, local_today)
        start = local_today - timedelta(days=RECOMMENDATION_DAYS - 1)

        meals = self.repo.list_between_days(uid, start.isoformat(), local_today.isoformat())
        if not meals:
            return {
                'text': 'Пока недостаточно данных для рекомендаций. Добавьте несколько приемов пищи.',
                'meals_analyzed': 0,
                'period': {
                    'from': start.isoformat(),
                    'to': local_today.isoformat(),
                },
                'kind': 'general',
                'title': 'Общая рекомендация',
                'limit': limit_before.to_dict(),
            }

        try:
            text = self.ai.generate_recommendations(
                build_recommendation_payload(
                    meals=meals,
                    date_from=start.isoformat(),
                    date_to=local_today.isoformat(),
                )
            )
        except AIExhaustedError as exc:
            raise ai_failed_exception() from exc

        limit_after = self.limiter.consume(uid, local_today, kind='general')
        return {
            'text': text,
            'meals_analyzed': len(meals),
            'period': {
                'from': start.isoformat(),
                'to': local_today.isoformat(),
            },
            'kind': 'general',
            'title': 'Общая рекомендация',
            'limit': limit_after.to_dict(),
        }

    def next_meal_recommendation(self, uid: str, timezone_name: str | None) -> dict:
        tz = self._resolve_tz(timezone_name)
        local_now = now_utc().astimezone(tz)
        local_today = local_now.date()
        limit_before = self.limiter.ensure_available(uid, local_today)
        start = local_today - timedelta(days=RECOMMENDATION_DAYS - 1)
        target_meal_type = infer_next_meal_type(local_now)
        title = f'Что мне съесть на {MEAL_TYPE_LABELS_RU[target_meal_type]}'

        meals = self.repo.list_between_days(uid, start.isoformat(), local_today.isoformat())
        if not meals:
            return {
                'text': 'Пока недостаточно данных для персональной рекомендации. Можно начать с простого приема пищи: источник белка, овощи и умеренная порция гарнира.',
                'meals_analyzed': 0,
                'period': {
                    'from': start.isoformat(),
                    'to': local_today.isoformat(),
                },
                'kind': 'next_meal',
                'title': title,
                'limit': limit_before.to_dict(),
            }

        payload = build_recommendation_payload(
            meals=meals,
            date_from=start.isoformat(),
            date_to=local_today.isoformat(),
        )
        payload['task'] = 'next_meal_recommendation'
        payload['target_meal'] = {
            'meal_type': target_meal_type.value,
            'meal_type_label': MEAL_TYPE_LABELS_RU[target_meal_type],
            'title': title,
        }
        payload['user_time'] = {
            'timezone': str(tz),
            'local_datetime': local_now.isoformat(),
            'local_date': local_today.isoformat(),
            'local_time': local_now.time().replace(microsecond=0).isoformat(),
        }

        try:
            text = self.ai.generate_next_meal_recommendation(payload)
        except AIExhaustedError as exc:
            raise ai_failed_exception() from exc

        limit_after = self.limiter.consume(uid, local_today, kind='next_meal')
        return {
            'text': text,
            'meals_analyzed': len(meals),
            'period': {
                'from': start.isoformat(),
                'to': local_today.isoformat(),
            },
            'kind': 'next_meal',
            'title': title,
            'limit': limit_after.to_dict(),
        }

    @staticmethod
    def _resolve_tz(timezone_name: str | None):
        try:
            return get_zoneinfo(timezone_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail='Invalid timezone') from exc


def infer_next_meal_type(local_dt: datetime) -> MealType:
    current = local_dt.time()
    if current < time(10, 30):
        return MealType.BREAKFAST
    if current < time(12, 0):
        return MealType.SECOND_BREAKFAST
    if current < time(15, 30):
        return MealType.LUNCH
    if current < time(17, 30):
        return MealType.AFTERNOON_SNACK
    if current < time(22, 30):
        return MealType.DINNER
    return MealType.BREAKFAST


def build_recommendation_payload(meals: list[dict], date_from: str, date_to: str) -> dict:
    calories_by_day: dict[str, float] = defaultdict(float)
    calories_by_type: dict[str, float] = {meal_type.value: 0.0 for meal_type in MealType}
    product_calories: dict[str, float] = defaultdict(float)
    product_portions: dict[str, float] = defaultdict(float)
    product_kcal_per_100g_sum: dict[str, float] = defaultdict(float)
    product_frequency: dict[str, int] = defaultdict(int)

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

            product_frequency[name] += 1
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
            'is_enough_for_strong_conclusions': days_with_entries >= 7 and meals_count >= 14,
            'warning': 'Данных мало. Делай только предварительные выводы.' if days_with_entries < 7 or meals_count < 14 else None,
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
        'top_products_by_frequency': [
            {'product_name': name, 'count': count}
            for name, count in sorted(product_frequency.items(), key=lambda item: item[1], reverse=True)[:10]
        ],
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
