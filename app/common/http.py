from fastapi import HTTPException, status

from app.core.config import get_settings


def ai_failed_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=get_settings().user_facing_ai_error,
    )
