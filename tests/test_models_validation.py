import pytest
from pydantic import ValidationError

from app.meals.models import MealUpdateRequest


def test_meal_update_consumed_at_requires_timezone():
    with pytest.raises(ValidationError):
        MealUpdateRequest(consumed_at="2026-06-19T21:30:00")


def test_meal_update_accepts_timezone_aware_consumed_at():
    payload = MealUpdateRequest(consumed_at="2026-06-19T21:30:00+03:00")
    assert payload.consumed_at.utcoffset() is not None
