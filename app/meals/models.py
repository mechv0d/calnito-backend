from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.common.enums import MealType


class PhotoInfo(BaseModel):
    storage_path: str | None = None
    signed_url: str | None = None
    width: int | None = None
    height: int | None = None


class MealItemBase(BaseModel):
    product_name: str = Field(min_length=1, max_length=120)
    portion_g: float = Field(gt=0, le=5000)
    kcal_per_100g: float = Field(ge=0, le=1000)
    confidence: float = Field(default=1.0, ge=0, le=1)


class MealItemResponse(MealItemBase):
    calories: float = Field(ge=0)


class MealItemUpdate(BaseModel):
    product_name: str = Field(min_length=1, max_length=120)
    portion_g: float = Field(gt=0, le=5000)
    kcal_per_100g: float = Field(ge=0, le=1000)
    confidence: float = Field(default=1.0, ge=0, le=1)


class MealTotals(BaseModel):
    calories: float = Field(ge=0)
    products_count: int = Field(ge=0)
    total_weight_g: float = Field(ge=0)


class MealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meal_type: MealType
    meal_type_label: str
    date_local: str
    consumed_at: datetime
    created_at: datetime
    updated_at: datetime
    description: str
    items: list[MealItemResponse]
    totals: MealTotals
    photo: PhotoInfo | None = None


class MealUpdateRequest(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    meal_type: MealType | None = None
    consumed_at: datetime | None = None
    items: list[MealItemUpdate] | None = Field(default=None, min_length=1, max_length=20)

    @field_validator('consumed_at')
    @classmethod
    def consumed_at_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('consumed_at must include timezone')
        return value



class MealsRangeResponse(BaseModel):
    date_from: str
    date_to: str
    meals: list[MealResponse]
    total_calories: float

class DayMealsResponse(BaseModel):
    date: str
    meals: list[MealResponse]
    total_calories: float


class TodaySummaryResponse(BaseModel):
    date: str
    total_calories: float
    by_meal_type: dict[str, float]
    meals_count: int
    meals: list[MealResponse]
