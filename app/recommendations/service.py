from collections import defaultdict
from datetime import datetime, time, timedelta
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException, status

from app.common.enums import MEAL_TYPE_LABELS_RU, MealType
from app.common.http import ai_failed_exception
from app.common.time import get_zoneinfo, now_utc
from app.llm.client import AIClient
from app.llm.exceptions import AIExhaustedError
from app.meals.repository import MealRepository
from app.recommendations.jobs import RecommendationJobRepository
from app.recommendations.usage import RecommendationLimiter


RECOMMENDATION_DAYS = 30


class RecommendationService:
    def __init__(self) -> None:
        self.repo = MealRepository()
        self.ai = AIClient()
        self.limiter = RecommendationLimiter()
        self.jobs = RecommendationJobRepository()

    def limits(self, uid: str, timezone_name: str | None) -> dict:
        tz = self._resolve_tz(timezone_name)
        today = now_utc().astimezone(tz).date()
        return self.limiter.status(uid, today).to_dict()

    def get_job(self, uid: str, job_id: str) -> dict:
        job = self.jobs.get(uid, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Recommendation job not found')
        return self._job_response(job)

    def queue_weekly_recommendations(
        self,
        uid: str,
        timezone_name: str | None,
        background_tasks: BackgroundTasks,
    ) -> dict:
        return self._queue_recommendation_job(
            uid=uid,
            timezone_name=timezone_name,
            kind='general',
            background_tasks=background_tasks,
        )

    def queue_next_meal_recommendation(
        self,
        uid: str,
        timezone_name: str | None,
        background_tasks: BackgroundTasks,
        target_meal_type: MealType | None = None,
    ) -> dict:
        return self._queue_recommendation_job(
            uid=uid,
            timezone_name=timezone_name,
            kind='next_meal',
            background_tasks=background_tasks,
            target_meal_type=target_meal_type,
        )

    def _queue_recommendation_job(
        self,
        uid: str,
        timezone_name: str | None,
        kind: str,
        background_tasks: BackgroundTasks,
        target_meal_type: MealType | None = None,
    ) -> dict:
        tz = self._resolve_tz(timezone_name)
        local_now = now_utc().astimezone(tz)
        local_today = local_now.date()
        limit_before = self.limiter.ensure_available(uid, local_today)
        start = local_today - timedelta(days=RECOMMENDATION_DAYS - 1)
        if kind == 'next_meal':
            target_meal_type = target_meal_type or infer_next_meal_type(local_now)
        else:
            target_meal_type = None
        title = 'Общая рекомендация'
        if target_meal_type is not None:
            title = f'Что мне съесть на {MEAL_TYPE_LABELS_RU[target_meal_type]}'

        job_id = uuid4().hex
        job = {
            'job_id': job_id,
            'uid': uid,
            'status': 'processing',
            'kind': kind,
            'title': title,
            'text': None,
            'meals_analyzed': 0,
            'period': {
                'from': start.isoformat(),
                'to': local_today.isoformat(),
            },
            'limit': limit_before.to_dict(),
            'error': None,
            'timezone_name': timezone_name,
            'target_meal_type': target_meal_type.value if target_meal_type else None,
            'user_time': {
                'timezone': str(tz),
                'local_datetime': local_now.isoformat(),
                'local_date': local_today.isoformat(),
                'local_time': local_now.time().replace(microsecond=0).isoformat(),
            },
            'created_at': now_utc(),
            'updated_at': now_utc(),
        }
        self.jobs.create(uid, job_id, job)
        background_tasks.add_task(complete_recommendation_job_task, uid=uid, job_id=job_id)
        return self._job_response(job)

    def complete_recommendation_job(self, uid: str, job_id: str) -> None:
        job = self.jobs.get(uid, job_id)
        if job is None or job.get('status') != 'processing':
            return

        period = job.get('period') or {}
        date_from = str(period.get('from'))
        date_to = str(period.get('to'))
        kind = str(job.get('kind') or 'general')
        title = str(job.get('title') or 'Рекомендации')

        try:
            meals = self.repo.list_between_days(uid, date_from, date_to)
            if not meals:
                fallback_text = 'Пока недостаточно данных для рекомендаций. Добавьте несколько приемов пищи.'
                if kind == 'next_meal':
                    fallback_text = 'Пока недостаточно данных для персональной рекомендации. Можно начать с простого приема пищи: источник белка, овощи и умеренная порция гарнира.'
                self.jobs.update(uid, job_id, {
                    'status': 'completed',
                    'text': fallback_text,
                    'meals_analyzed': 0,
                    'updated_at': now_utc(),
                    'error': None,
                })
                return

            payload = build_recommendation_payload(
                meals=meals,
                date_from=date_from,
                date_to=date_to,
            )

            if kind == 'next_meal':
                target_meal_type = MealType(job.get('target_meal_type') or MealType.BREAKFAST.value)
                payload['task'] = 'next_meal_recommendation'
                payload['target_meal'] = {
                    'meal_type': target_meal_type.value,
                    'meal_type_label': MEAL_TYPE_LABELS_RU[target_meal_type],
                    'title': title,
                }
                payload['user_time'] = job.get('user_time') or {}
                text = self.ai.generate_next_meal_recommendation(payload)
            else:
                text = self.ai.generate_recommendations(payload)

            local_date = datetime.fromisoformat(date_to).date()
            limit_after = self.limiter.consume(uid, local_date, kind=kind)
            self.jobs.update(uid, job_id, {
                'status': 'completed',
                'text': text,
                'meals_analyzed': len(meals),
                'limit': limit_after.to_dict(),
                'updated_at': now_utc(),
                'error': None,
            })
        except AIExhaustedError as exc:
            self.jobs.update(uid, job_id, {
                'status': 'failed',
                'error': ai_failed_exception().detail,
                'updated_at': now_utc(),
                'llm_error': repr(exc),
            })
        except Exception as exc:
            self.jobs.update(uid, job_id, {
                'status': 'failed',
                'error': 'Не удалось подготовить рекомендацию. Попробуйте позже.',
                'updated_at': now_utc(),
                'llm_error': repr(exc),
            })

    @staticmethod
    def _job_response(job: dict) -> dict:
        return {
            'job_id': job.get('job_id'),
            'status': job.get('status') or 'processing',
            'kind': job.get('kind') or 'general',
            'title': job.get('title'),
            'text': job.get('text'),
            'meals_analyzed': int(job.get('meals_analyzed') or 0),
            'period': job.get('period') or {},
            'limit': job.get('limit'),
            'error': job.get('error'),
        }

    @staticmethod
    def _resolve_tz(timezone_name: str | None):
        try:
            return get_zoneinfo(timezone_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail='Invalid timezone') from exc




def complete_recommendation_job_task(uid: str, job_id: str) -> None:
    RecommendationService().complete_recommendation_job(uid=uid, job_id=job_id)


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
