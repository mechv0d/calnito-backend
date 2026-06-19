from app.llm.schemas import ParsedFoodItem, ParsedMeal
from app.meals.calculations import (
    build_items_from_manual,
    build_items_from_parsed,
    calculate_calories,
    calculate_totals,
)
from app.meals.models import MealItemUpdate


def test_calculate_calories_rounds_to_one_decimal():
    assert calculate_calories(33.33, 250) == 83.3


def test_build_items_from_parsed_normalizes_and_calculates():
    parsed = ParsedMeal(
        items=[
            ParsedFoodItem(product_name=" Омлет ", portion_g=180.04, kcal_per_100g=154.04, confidence=0.876),
        ],
        notes=None,
    )

    items = build_items_from_parsed(parsed)

    assert items == [
        {
            "product_name": "омлет",
            "portion_g": 180.0,
            "kcal_per_100g": 154.0,
            "calories": 277.3,
            "confidence": 0.88,
        }
    ]


def test_build_items_from_manual_and_totals():
    items = build_items_from_manual(
        [
            MealItemUpdate(product_name=" Хлеб ", portion_g=40, kcal_per_100g=250, confidence=1),
            MealItemUpdate(product_name="Сыр", portion_g=20, kcal_per_100g=360, confidence=0.95),
        ]
    )

    assert items[0]["product_name"] == "хлеб"
    assert items[0]["calories"] == 100
    assert calculate_totals(items) == {
        "calories": 172,
        "products_count": 2,
        "total_weight_g": 60,
    }
