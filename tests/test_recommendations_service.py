import pytest
from fastapi import HTTPException

import app.recommendations.service as recommendation_module
from app.llm.exceptions import AIExhaustedError
from app.recommendations.service import RecommendationService


class FakeRepo:
    def __init__(self, meals):
        self.meals = meals

    def list_between_days(self, uid, start, end):
        self.args = (uid, start, end)
        return self.meals


class FakeAI:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def generate_recommendations(self, payload):
        self.calls.append(payload)
        if self.fail:
            raise AIExhaustedError("dead")
        return "Добавь овощей."


def make_service(meals, fail=False):
    service = object.__new__(RecommendationService)
    service.repo = FakeRepo(meals)
    service.ai = FakeAI(fail=fail)
    return service


def test_weekly_recommendations_returns_not_enough_data_when_no_meals(monkeypatch, frozen_dt):
    monkeypatch.setattr(recommendation_module, "now_utc", lambda: frozen_dt)
    service = make_service([])

    result = service.weekly_recommendations("u1", "UTC")

    assert result["meals_analyzed"] == 0
    assert "недостаточно данных" in result["text"].lower()
    assert result["period"] == {"from": "2026-05-21", "to": "2026-06-19"}
    assert service.ai.calls == []


def test_weekly_recommendations_uses_ai_for_existing_meals(monkeypatch, frozen_dt, sample_meal):
    monkeypatch.setattr(recommendation_module, "now_utc", lambda: frozen_dt)
    lunch = {
        **sample_meal,
        "id": "meal-2",
        "description": "rice and chicken",
        "meal_type": "lunch",
        "date_local": "2026-06-18",
        "items": [
            {
                "product_name": "rice",
                "portion_g": 150,
                "kcal_per_100g": 130,
                "calories": 195,
                "confidence": 0.9,
            },
            {
                "product_name": "chicken",
                "portion_g": 120,
                "kcal_per_100g": 165,
                "calories": 198,
                "confidence": 0.9,
            },
        ],
        "totals": {"calories": 393, "products_count": 2, "total_weight_g": 270},
    }
    service = make_service([sample_meal, lunch])

    result = service.weekly_recommendations("u1", "UTC")

    assert result["text"] == "Добавь овощей."
    assert result["meals_analyzed"] == 2
    assert service.repo.args == ("u1", "2026-05-21", "2026-06-19")

    payload = service.ai.calls[0]
    assert payload["task"] == "nutrition_recommendations"
    assert payload["language"] == "ru"
    assert payload["data_quality"] == {"period_days": 30, "days_with_entries": 2, "meals_count": 2}
    assert payload["summary"] == {
        "total_logged_calories": 670.2,
        "average_logged_calories_per_day_with_entries": 335.1,
        "average_logged_calories_per_meal": 335.1,
    }
    assert payload["meals"][0] == {
        "date_local": "2026-06-19",
        "meal_type": "breakfast",
        "description": sample_meal["description"],
        "total_calories": 277.2,
        "items": [
            {
                "product_name": sample_meal["items"][0]["product_name"],
                "portion_g": 180.0,
                "calories": 277.2,
                "kcal_per_100g": 154.0,
            }
        ],
    }
    assert payload["top_products_by_calories"][0] == {
        "product_name": sample_meal["items"][0]["product_name"],
        "calories": 277.2,
        "kcal_per_100g": 154.0,
    }
    assert payload["calories_by_day"] == {"2026-06-18": 393.0, "2026-06-19": 277.2}
    assert payload["calories_by_meal_type"]["breakfast"] == 277.2
    assert payload["calories_by_meal_type"]["lunch"] == 393.0


def test_weekly_recommendations_returns_boss_error_on_ai_failure(monkeypatch, frozen_dt, sample_meal):
    monkeypatch.setattr(recommendation_module, "now_utc", lambda: frozen_dt)
    service = make_service([sample_meal], fail=True)

    with pytest.raises(HTTPException) as exc:
        service.weekly_recommendations("u1", "UTC")

    assert exc.value.status_code == 503
    assert exc.value.detail == "Мы проебались, Босс."
