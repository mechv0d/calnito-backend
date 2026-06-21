import logging
import time
from dataclasses import dataclass

from fastapi import Header, HTTPException, status
from firebase_admin import auth

from app.core.config import get_settings
from app.core.firebase import get_firebase_app

logger = logging.getLogger(__name__)

# Token verification is still performed by Firebase Admin.
# The small in-process cache only avoids repeating the same verification during SPA navigation
# and React/dev duplicate requests. It is disabled automatically when FIREBASE_CHECK_REVOKED=true.
_TOKEN_CACHE_TTL_SECONDS = 300
_token_cache: dict[str, tuple[float, 'CurrentUser']] = {}


@dataclass(frozen=True)
class CurrentUser:
    uid: str
    email: str | None = None


def _get_cached_user(token: str) -> CurrentUser | None:
    cached = _token_cache.get(token)
    if cached is None:
        return None

    expires_at, user = cached
    if expires_at <= time.time():
        _token_cache.pop(token, None)
        return None

    return user


def _cache_user(token: str, decoded: dict, user: CurrentUser) -> None:
    exp = decoded.get('exp')
    now = time.time()
    token_expires_at = float(exp) if isinstance(exp, int | float) else now + _TOKEN_CACHE_TTL_SECONDS
    cache_expires_at = min(token_expires_at, now + _TOKEN_CACHE_TTL_SECONDS)

    if cache_expires_at > now:
        _token_cache[token] = (cache_expires_at, user)


def _verify_firebase_token(token: str) -> dict:
    settings = get_settings()
    started = time.perf_counter()

    try:
        get_firebase_app()
        return auth.verify_id_token(token, check_revoked=settings.firebase_check_revoked)
    except Exception as exc:
        logger.exception('Firebase token verification failed')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid Firebase token',
        ) from exc
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        log = logger.warning if elapsed_ms >= 1000 else logger.debug
        log('Firebase token verification took %.1fms', elapsed_ms)


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
    if not settings.firebase_check_revoked:
        cached_user = _get_cached_user(token)
        if cached_user is not None:
            return cached_user

    decoded = _verify_firebase_token(token)

    if decoded.get('email_verified') is not True:
        started = time.perf_counter()
        user_record = auth.get_user(decoded['uid'])
        elapsed_ms = (time.perf_counter() - started) * 1000
        log = logger.warning if elapsed_ms >= 1000 else logger.debug
        log('Firebase get_user took %.1fms', elapsed_ms)

        if user_record.email_verified:
            user = CurrentUser(uid=decoded['uid'], email=decoded.get('email') or user_record.email)
            if not settings.firebase_check_revoked:
                _cache_user(token, decoded, user)
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Email is not verified',
        )

    user = CurrentUser(uid=decoded['uid'], email=decoded.get('email'))
    if not settings.firebase_check_revoked:
        _cache_user(token, decoded, user)
    return user
