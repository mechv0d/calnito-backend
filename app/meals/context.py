from app.common.enums import MealType
from app.meals.repository import MealRepository


def extract_products_from_meals(meals: list[dict], limit: int = 10) -> list[dict]:
    result: list[dict] = []
    seen: set[tuple[str, float]] = set()

    for meal in meals:
        for item in meal.get('items', []):
            name = str(item.get('product_name', '')).strip().lower()
            kcal = float(item.get('kcal_per_100g', 0) or 0)
            if not name or kcal <= 0:
                continue
            key = (name, kcal)
            if key in seen:
                continue
            seen.add(key)
            result.append({
                'product_name': name,
                'kcal_per_100g': kcal,
            })
            if len(result) >= limit:
                return result

    return result


class FoodContextService:
    def __init__(self, repo: MealRepository | None = None) -> None:
        self.repo = repo or MealRepository()

    def recent_products(self, uid: str, limit: int = 10) -> list[dict]:
        meals = self.repo.list_recent(uid, limit=30)
        return extract_products_from_meals(meals, limit=limit)

    def recent_products_by_type(self, uid: str, meal_type: MealType, limit: int = 10) -> list[dict]:
        meals = self.repo.list_recent_by_type(uid, meal_type=meal_type, limit=30)
        return extract_products_from_meals(meals, limit=limit)
