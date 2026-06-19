from pydantic import BaseModel


class RecommendationResponse(BaseModel):
    text: str
    meals_analyzed: int
    period: dict[str, str]
