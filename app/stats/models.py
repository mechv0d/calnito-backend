from pydantic import BaseModel


class Period(BaseModel):
    date_from: str
    date_to: str


class Totals(BaseModel):
    calories: float
    meals_count: int
    days_count: int
    products_count: int


class Averages(BaseModel):
    calories_per_day: float
    calories_per_meal: float
    products_per_meal: float
    weight_per_meal_g: float


class ProductCalories(BaseModel):
    product_name: str
    calories: float


class StatsResponse(BaseModel):
    period: Period
    totals: Totals
    averages: Averages
    calories_by_day: dict[str, float]
    calories_by_meal_type: dict[str, float]
    top_products_by_frequency: list[tuple[str, int]]
    top_products_by_calories: list[ProductCalories]
