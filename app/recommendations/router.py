from fastapi import APIRouter, BackgroundTasks, Depends, Header

from app.auth.dependencies import CurrentUser, get_current_user
from app.recommendations.models import NextMealRecommendationRequest, RecommendationJobResponse, RecommendationLimitResponse
from app.recommendations.service import RecommendationService

router = APIRouter(prefix='/recommendations', tags=['recommendations'])


@router.get('/limits', response_model=RecommendationLimitResponse)
def get_recommendation_limits(
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return RecommendationService().limits(uid=user.uid, timezone_name=timezone_name)


@router.get('/jobs/{job_id}', response_model=RecommendationJobResponse)
def get_recommendation_job(
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return RecommendationService().get_job(uid=user.uid, job_id=job_id)


@router.post('', response_model=RecommendationJobResponse)
def get_weekly_recommendations(
    background_tasks: BackgroundTasks,
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return RecommendationService().queue_weekly_recommendations(
        uid=user.uid,
        timezone_name=timezone_name,
        background_tasks=background_tasks,
    )


@router.post('/next-meal', response_model=RecommendationJobResponse)
def get_next_meal_recommendation(
    background_tasks: BackgroundTasks,
    payload: NextMealRecommendationRequest | None = None,
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return RecommendationService().queue_next_meal_recommendation(
        uid=user.uid,
        timezone_name=timezone_name,
        background_tasks=background_tasks,
        target_meal_type=payload.meal_type if payload else None,
    )
