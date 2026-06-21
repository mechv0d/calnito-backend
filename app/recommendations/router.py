from fastapi import APIRouter, Depends, Header

from app.auth.dependencies import CurrentUser, get_current_user
from app.recommendations.models import RecommendationLimitResponse, RecommendationResponse
from app.recommendations.service import RecommendationService

router = APIRouter(prefix='/recommendations', tags=['recommendations'])


@router.get('/limits', response_model=RecommendationLimitResponse)
def get_recommendation_limits(
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return RecommendationService().limits(uid=user.uid, timezone_name=timezone_name)


@router.post('', response_model=RecommendationResponse)
def get_weekly_recommendations(
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return RecommendationService().weekly_recommendations(uid=user.uid, timezone_name=timezone_name)


@router.post('/next-meal', response_model=RecommendationResponse)
def get_next_meal_recommendation(
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return RecommendationService().next_meal_recommendation(uid=user.uid, timezone_name=timezone_name)
