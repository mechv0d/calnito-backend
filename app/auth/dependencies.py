from dataclasses import dataclass

from fastapi import Header, HTTPException, status
from firebase_admin import auth

from app.core.config import get_settings
from app.core.firebase import get_firebase_app

import logging # TODO: Remove this when done debugging

logger = logging.getLogger(__name__) # TODO: Remove this when done debugging


@dataclass(frozen=True)
class CurrentUser:
    uid: str
    email: str | None = None


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing Firebase bearer token',
        )

    token = authorization.removeprefix('Bearer ').strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing Firebase bearer token',
        )

    settings = get_settings()
    try:
        get_firebase_app()
        decoded = auth.verify_id_token(token, check_revoked=settings.firebase_check_revoked)
    except Exception as exc:
        logger.exception("Firebase token verification failed")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid Firebase token: {type(exc).__name__}: {exc}", # TODO: Remove this when done debugging
        )

    return CurrentUser(uid=decoded['uid'], email=decoded.get('email'))
