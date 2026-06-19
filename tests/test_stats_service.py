from app.stats.service import StatsService


class FakeRepo:
    def __init__(self, meals):
        self.meals = meals

    def list_between_days(self, uid, date_from, date_to):
        self.args = (uid, date_from, date_to)
        return self.meals


def test_stats_service_builds_metrics(sample_meal):
    meal2 = {
        **sample_meal,
        "id": "meal-2",
        "date_local": "2026-06-20",
        "meal_type": "lunch",
        "items": [
            {"product_name": "хлеб", "calories": 100},
            {"product_name": "омлет", "calories": 200},
        ],
        "totals": {"calories": 300, "products_count": 2, "total_weight_g": 220},
    }
    service = StatsService()
    service.repo = FakeRepo([sample_meal, meal2])

    result = service.build_stats("u1", "2026-06-19", "2026-06-20")

    assert result["totals"] == {
        "calories": 577.2,
        "meals_count": 2,
        "days_count": 2,
        "products_count": 3,
    }
    assert result["averages"]["calories_per_day"] == 288.6
    assert result["calories_by_meal_type"]["breakfast"] == 277.2
    assert result["calories_by_meal_type"]["lunch"] == 300
    assert result["top_products_by_frequency"][0] == ("омлет", 2)
    assert result["top_products_by_calories"][0] == {"product_name": "омлет", "calories": 477.2}


def test_stats_service_handles_empty_period():
    service = StatsService()
    service.repo = FakeRepo([])

    result = service.build_stats("u1", "2026-06-19", "2026-06-20")

    assert result["totals"]["calories"] == 0
    assert result["averages"]["calories_per_day"] == 0
    assert result["averages"]["calories_per_meal"] == 0
