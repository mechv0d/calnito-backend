from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile, status

from app.auth.dependencies import CurrentUser, get_current_user
from app.meals.models import DayMealsResponse, ManualMealCreateRequest, MealPhotoUrlResponse, MealResponse, MealsRangeResponse, MealUpdateRequest, ProductSuggestionsResponse, TodaySummaryResponse
from app.meals.service import MealService

router = APIRouter(prefix='/meals', tags=['meals'])


@router.post('', response_model=MealResponse, status_code=status.HTTP_201_CREATED)
async def create_meal(
    description: str = Form(..., min_length=1, max_length=2000),
    photo: UploadFile | None = File(default=None),
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return await MealService().create_meal(
        uid=user.uid,
        description=description,
        timezone_name=timezone_name,
        photo=photo,
    )


@router.post('/manual', response_model=MealResponse, status_code=status.HTTP_201_CREATED)
def create_manual_meal(
    payload: ManualMealCreateRequest,
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return MealService().create_manual_meal(
        uid=user.uid,
        payload=payload,
        timezone_name=timezone_name,
    )


@router.get('/products/popular', response_model=ProductSuggestionsResponse)
def search_popular_products(
    q: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user: CurrentUser = Depends(get_current_user),
):
    return MealService().search_product_suggestions(
        uid=user.uid,
        query=q,
        page=page,
        page_size=page_size,
    )



@router.get('', response_model=MealsRangeResponse)
def get_meals_range(
    date_from: str = Query(..., alias='from'),
    date_to: str = Query(..., alias='to'),
    user: CurrentUser = Depends(get_current_user),
):
    return MealService().get_between_days(uid=user.uid, date_from=date_from, date_to=date_to)


@router.get('/today', response_model=TodaySummaryResponse)
def get_today_summary(
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return MealService().get_today_summary(uid=user.uid, timezone_name=timezone_name)



@router.get('/summary/today', response_model=TodaySummaryResponse)
def get_today_summary_alias(
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return MealService().get_today_summary(uid=user.uid, timezone_name=timezone_name)


@router.get('/by-day', response_model=DayMealsResponse)
def get_meals_by_day(
    date: str,
    user: CurrentUser = Depends(get_current_user),
):
    return MealService().get_by_day(uid=user.uid, date_local=date)


@router.get('/{meal_id}/photo-url', response_model=MealPhotoUrlResponse)
def get_meal_photo_url(
    meal_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return MealService().get_meal_photo_url(uid=user.uid, meal_id=meal_id)


@router.get('/{meal_id}', response_model=MealResponse)
def get_meal(
    meal_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return MealService().get_meal(uid=user.uid, meal_id=meal_id)


@router.patch('/{meal_id}', response_model=MealResponse)
def update_meal(
    meal_id: str,
    payload: MealUpdateRequest,
    timezone_name: str | None = Header(default=None, alias='X-Timezone'),
    user: CurrentUser = Depends(get_current_user),
):
    return MealService().update_meal(
        uid=user.uid,
        meal_id=meal_id,
        payload=payload,
        timezone_name=timezone_name,
    )


@router.delete('/{meal_id}')
def delete_meal(
    meal_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    return MealService().delete_meal(uid=user.uid, meal_id=meal_id)
