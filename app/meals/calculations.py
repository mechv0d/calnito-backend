from app.llm.schemas import ParsedMeal
from app.meals.models import MealItemUpdate


def calculate_calories(portion_g: float, kcal_per_100g: float) -> float:
    return round(portion_g * kcal_per_100g / 100, 1)


def build_items_from_parsed(parsed: ParsedMeal) -> list[dict]:
    return [
        {
            'product_name': item.product_name.strip().lower(),
            'portion_g': round(float(item.portion_g), 1),
            'kcal_per_100g': round(float(item.kcal_per_100g), 1),
            'calories': calculate_calories(item.portion_g, item.kcal_per_100g),
            'confidence': round(float(item.confidence), 2),
        }
        for item in parsed.items
    ]


def build_items_from_manual(items: list[MealItemUpdate]) -> list[dict]:
    result = []
    for item in items:
        portion_g = round(float(item.portion_g), 1)
        kcal_per_100g = round(float(item.kcal_per_100g), 1)
        result.append({
            'product_name': item.product_name.strip().lower(),
            'portion_g': portion_g,
            'kcal_per_100g': kcal_per_100g,
            'calories': calculate_calories(portion_g, kcal_per_100g),
            'confidence': round(float(item.confidence), 2),
        })
    return result


def calculate_totals(items: list[dict]) -> dict:
    return {
        'calories': round(sum(float(item.get('calories', 0)) for item in items), 1),
        'products_count': len(items),
        'total_weight_g': round(sum(float(item.get('portion_g', 0)) for item in items), 1),
    }
