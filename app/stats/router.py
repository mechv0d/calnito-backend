from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import CurrentUser, get_current_user
from app.stats.models import StatsResponse
from app.stats.service import StatsService

router = APIRouter(prefix='/stats', tags=['stats'])


@router.get('', response_model=StatsResponse)
def get_stats(
    date_from: str = Query(..., alias='from'),
    date_to: str = Query(..., alias='to'),
    user: CurrentUser = Depends(get_current_user),
):
    return StatsService().build_stats(uid=user.uid, date_from=date_from, date_to=date_to)
