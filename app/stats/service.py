from collections import Counter, defaultdict

from app.common.enums import MealType
from app.meals.repository import MealRepository


class StatsService:
    def __init__(self) -> None:
        self.repo = MealRepository()

    def build_stats(self, uid: str, date_from: str, date_to: str) -> dict:
        meals = self.repo.list_between_days(uid, date_from, date_to)

        calories_by_day: dict[str, float] = defaultdict(float)
        calories_by_type: dict[str, float] = {meal_type.value: 0.0 for meal_type in MealType}
        product_frequency: Counter[str] = Counter()
        product_calories: dict[str, float] = defaultdict(float)

        total_calories = 0.0
        total_weight = 0.0
        total_products = 0

        for meal in meals:
            meal_calories = float(meal.get('totals', {}).get('calories', 0))
            total_calories += meal_calories
            calories_by_day[meal['date_local']] += meal_calories
            calories_by_type[meal['meal_type']] = calories_by_type.get(meal['meal_type'], 0.0) + meal_calories

            total_weight += float(meal.get('totals', {}).get('total_weight_g', 0))
            total_products += int(meal.get('totals', {}).get('products_count', 0))

            for item in meal.get('items', []):
                name = str(item.get('product_name', '')).strip().lower()
                if not name:
                    continue
                product_frequency[name] += 1
                product_calories[name] += float(item.get('calories', 0))

        meals_count = len(meals)
        days_count = len(calories_by_day)
        safe_days_count = max(days_count, 1)

        return {
            'period': {
                'date_from': date_from,
                'date_to': date_to,
            },
            'totals': {
                'calories': round(total_calories, 1),
                'meals_count': meals_count,
                'days_count': days_count,
                'products_count': total_products,
            },
            'averages': {
                'calories_per_day': round(total_calories / safe_days_count, 1),
                'calories_per_meal': round(total_calories / meals_count, 1) if meals_count else 0,
                'products_per_meal': round(total_products / meals_count, 1) if meals_count else 0,
                'weight_per_meal_g': round(total_weight / meals_count, 1) if meals_count else 0,
            },
            'calories_by_day': {
                day: round(value, 1)
                for day, value in sorted(calories_by_day.items())
            },
            'calories_by_meal_type': {
                meal_type: round(value, 1)
                for meal_type, value in calories_by_type.items()
            },
            'top_products_by_frequency': product_frequency.most_common(10),
            'top_products_by_calories': sorted(
                [
                    {
                        'product_name': name,
                        'calories': round(calories, 1),
                    }
                    for name, calories in product_calories.items()
                ],
                key=lambda x: x['calories'],
                reverse=True,
            )[:10],
        }
