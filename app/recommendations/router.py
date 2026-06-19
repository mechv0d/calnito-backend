from fastapi import APIRouter, Depends, Header

from app.auth.dependencies import CurrentUser, get_current_user
from app.recommendations.models import RecommendationResponse
from app.recommendations.service import RecommendationService

router = APIRouter(prefix='/recommendations', tags=['recommendations'])


@router.post('', response_model=RecommendationResponse)
def get_weekly_recommendations(
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return RecommendationService().weekly_recommendations(uid=user.uid, timezone_name=timezone_name)
