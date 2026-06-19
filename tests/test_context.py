from app.common.enums import MealType
from app.meals.context import FoodContextService, extract_products_from_meals


class FakeRepo:
    def __init__(self, meals):
        self.meals = meals
        self.recent_calls = []
        self.by_type_calls = []

    def list_recent(self, uid: str, limit: int):
        self.recent_calls.append((uid, limit))
        return self.meals

    def list_recent_by_type(self, uid: str, meal_type: MealType, limit: int):
        self.by_type_calls.append((uid, meal_type, limit))
        return self.meals


def test_extract_products_skips_duplicates_empty_names_and_zero_kcal():
    meals = [
        {
            "items": [
                {"product_name": " Омлет ", "kcal_per_100g": 154},
                {"product_name": "омлет", "kcal_per_100g": 154},
                {"product_name": "", "kcal_per_100g": 100},
                {"product_name": "вода", "kcal_per_100g": 0},
                {"product_name": "хлеб", "kcal_per_100g": 250},
            ]
        }
    ]

    assert extract_products_from_meals(meals, limit=10) == [
        {"product_name": "омлет", "kcal_per_100g": 154.0},
        {"product_name": "хлеб", "kcal_per_100g": 250.0},
    ]


def test_context_service_delegates_to_repo_with_wider_limit():
    repo = FakeRepo([{"items": [{"product_name": "сыр", "kcal_per_100g": 360}]}])
    service = FoodContextService(repo)

    assert service.recent_products("u1") == [{"product_name": "сыр", "kcal_per_100g": 360.0}]
    assert service.recent_products_by_type("u1", MealType.BREAKFAST) == [
        {"product_name": "сыр", "kcal_per_100g": 360.0}
    ]
    assert repo.recent_calls == [("u1", 30)]
    assert repo.by_type_calls == [("u1", MealType.BREAKFAST, 30)]
