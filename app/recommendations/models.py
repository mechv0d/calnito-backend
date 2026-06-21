from pydantic import BaseModel, Field


class RecommendationLimitResponse(BaseModel):
    used: int = Field(ge=0)
    limit: int = Field(ge=0)
    remaining: int = Field(ge=0)
    week_key: str


class RecommendationResponse(BaseModel):
    text: str
    meals_analyzed: int
    period: dict
    kind: str = 'general'
    title: str | None = None
    limit: RecommendationLimitResponse | None = None
