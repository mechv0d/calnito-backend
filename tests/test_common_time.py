from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.common.enums import MealType
from app.common.time import get_zoneinfo, infer_meal_type, local_date_string


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [
        (5, 0, MealType.BREAKFAST),
        (10, 29, MealType.BREAKFAST),
        (10, 30, MealType.SECOND_BREAKFAST),
        (11, 59, MealType.SECOND_BREAKFAST),
        (12, 0, MealType.LUNCH),
        (15, 29, MealType.LUNCH),
        (15, 30, MealType.AFTERNOON_SNACK),
        (17, 29, MealType.AFTERNOON_SNACK),
        (17, 30, MealType.DINNER),
        (4, 59, MealType.DINNER),
    ],
)
def test_infer_meal_type_boundaries(hour, minute, expected):
    dt = datetime(2026, 6, 19, hour, minute, tzinfo=ZoneInfo("Europe/Helsinki"))
    assert infer_meal_type(dt) == expected


def test_local_date_string_uses_given_timezone():
    dt_utc = datetime(2026, 6, 18, 22, 30, tzinfo=ZoneInfo("UTC"))
    assert local_date_string(dt_utc, ZoneInfo("Europe/Helsinki")) == "2026-06-19"


def test_get_zoneinfo_rejects_invalid_timezone():
    with pytest.raises(ValueError):
        get_zoneinfo("Bad/Timezone")
