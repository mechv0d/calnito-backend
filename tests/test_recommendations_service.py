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

    def generate_recommendations(self, meals):
        self.calls.append(meals)
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
    assert result["period"] == {"from": "2026-06-13", "to": "2026-06-19"}
    assert service.ai.calls == []


def test_weekly_recommendations_uses_ai_for_existing_meals(monkeypatch, frozen_dt, sample_meal):
    monkeypatch.setattr(recommendation_module, "now_utc", lambda: frozen_dt)
    service = make_service([sample_meal])

    result = service.weekly_recommendations("u1", "UTC")

    assert result["text"] == "Добавь овощей."
    assert result["meals_analyzed"] == 1


def test_weekly_recommendations_returns_boss_error_on_ai_failure(monkeypatch, frozen_dt, sample_meal):
    monkeypatch.setattr(recommendation_module, "now_utc", lambda: frozen_dt)
    service = make_service([sample_meal], fail=True)

    with pytest.raises(HTTPException) as exc:
        service.weekly_recommendations("u1", "UTC")

    assert exc.value.status_code == 503
    assert exc.value.detail == "Мы проебались, Босс."
