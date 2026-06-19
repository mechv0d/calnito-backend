import re
from typing import Any


class FoodResponseNormalizationError(ValueError):
    pass


def _first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def _to_float(value: Any, field_name: str) -> float:
    if isinstance(value, int | float):
        return float(value)

    if isinstance(value, str):
        normalized = value.strip().replace(",", ".")
        match = re.search(r"-?\d+(\.\d+)?", normalized)
        if match:
            return float(match.group(0))

    raise FoodResponseNormalizationError(f"Invalid numeric field: {field_name}")


def _normalize_item(raw_item: Any) -> dict[str, Any] | None:
    if not isinstance(raw_item, dict):
        return None

    product_name = _first_present(
        raw_item,
        "product_name",
        "product",
        "name",
        "food",
        "food_name",
        "title",
    )

    portion_g = _first_present(
        raw_item,
        "portion_g",
        "portion",
        "weight_g",
        "weight",
        "grams",
        "amount_g",
        "serving_g",
    )

    kcal_per_100g = _first_present(
        raw_item,
        "kcal_per_100g",
        "calories_per_100g",
        "calories_100g",
        "kcal_100g",
        "calorie_per_100g",
        "caloriesPer100g",
        "kcalPer100g",
    )

    confidence = _first_present(
        raw_item,
        "confidence",
        "certainty",
        "probability",
    )

    if product_name is None or portion_g is None or kcal_per_100g is None:
        return None

    confidence_value = 0.65 if confidence is None else _to_float(confidence, "confidence")
    confidence_value = max(0.0, min(1.0, confidence_value))

    return {
        "product_name": str(product_name).strip().lower(),
        "portion_g": _to_float(portion_g, "portion_g"),
        "kcal_per_100g": _to_float(kcal_per_100g, "kcal_per_100g"),
        "confidence": confidence_value,
    }


def normalize_food_parse_payload(payload: Any) -> dict[str, Any]:
    """
    Converts common LLM mistakes into our strict ParsedMeal schema.

    Supported inputs:
    - {"items": [...]}
    - {"products": [...]}
    - {"foods": [...]}
    - raw list: [...]
    """

    if isinstance(payload, list):
        payload = {"items": payload}

    if not isinstance(payload, dict):
        raise FoodResponseNormalizationError("AI response must be object or list")

    raw_items = (
        payload.get("items")
        or payload.get("products")
        or payload.get("foods")
        or payload.get("food_items")
        or payload.get("meal_items")
    )

    if not isinstance(raw_items, list):
        raise FoodResponseNormalizationError("AI response does not contain items/products list")

    items = []

    for raw_item in raw_items:
        normalized_item = _normalize_item(raw_item)
        if normalized_item is not None:
            items.append(normalized_item)

    if not items:
        raise FoodResponseNormalizationError("AI response contains no valid food items")

    notes = payload.get("notes")

    return {
        "items": items,
        "notes": notes if isinstance(notes, str) else None,
    }