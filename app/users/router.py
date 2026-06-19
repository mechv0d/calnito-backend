from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser, get_current_user
from app.users.models import UserProfileResponse, UserProfileUpdate
from app.users.service import UserService

router = APIRouter(prefix='/users', tags=['users'])


@router.get('/me', response_model=UserProfileResponse)
def get_me(user: CurrentUser = Depends(get_current_user)):
    return UserService().get_or_create_profile(uid=user.uid, email=user.email)


@router.patch('/me', response_model=UserProfileResponse)
def update_me(payload: UserProfileUpdate, user: CurrentUser = Depends(get_current_user)):
    return UserService().update_profile(uid=user.uid, email=user.email, timezone_name=payload.timezone)
