from pydantic import BaseModel, Field

from app.common.enums import MealType


class RecommendationLimitResponse(BaseModel):
    used: int = Field(ge=0)
    limit: int = Field(ge=0)
    remaining: int = Field(ge=0)
    week_key: str


class NextMealRecommendationRequest(BaseModel):
    meal_type: MealType | None = None


class RecommendationResponse(BaseModel):
    text: str
    meals_analyzed: int
    period: dict
    kind: str = 'general'
    title: str | None = None
    limit: RecommendationLimitResponse | None = None


class RecommendationJobResponse(BaseModel):
    job_id: str
    status: str
    kind: str = 'general'
    title: str | None = None
    text: str | None = None
    meals_analyzed: int = 0
    period: dict = Field(default_factory=dict)
    limit: RecommendationLimitResponse | None = None
    error: str | None = None
