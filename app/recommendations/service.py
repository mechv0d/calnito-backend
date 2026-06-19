from datetime import timedelta

from app.common.http import ai_failed_exception
from app.common.time import get_zoneinfo, local_date_string, now_utc
from app.llm.client import AIClient
from app.llm.exceptions import AIExhaustedError
from app.meals.repository import MealRepository


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
        start = today - timedelta(days=6)

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
            text = self.ai.generate_recommendations(meals)
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
