import base64
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from firebase_admin import auth

from app.core.firebase import get_firebase_app, get_firestore_client
from app.storage.supabase_storage import get_supabase_client

logger = logging.getLogger(__name__)


def _measure_step(name: str, callback: Callable[[], None]) -> None:
    started = time.perf_counter()
    try:
        callback()
    except Exception:
        logger.exception('Warmup step failed: %s', name)
        return

    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info('Warmup step completed: %s %.1fms', name, elapsed_ms)


def _json_b64url(payload: dict) -> str:
    raw = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _build_unsigned_firebase_like_token(project_id: str | None) -> str:
    now = datetime.now(timezone.utc)
    iat = int(now.timestamp())
    exp = int((now + timedelta(hours=1)).timestamp())
    project = project_id or 'unknown-project'

    header = {
        'alg': 'RS256',
        'kid': 'calnito-warmup',
        'typ': 'JWT',
    }
    payload = {
        'aud': project,
        'iss': f'https://securetoken.google.com/{project}',
        'sub': 'calnito-warmup',
        'user_id': 'calnito-warmup',
        'iat': iat,
        'exp': exp,
        'auth_time': iat,
        'firebase': {'sign_in_provider': 'custom'},
    }
    return f'{_json_b64url(header)}.{_json_b64url(payload)}.invalid-signature'


def _warm_firebase_admin() -> None:
    get_firebase_app()


def _warm_firebase_auth_verifier() -> None:
    """
    Firebase Admin fetches Google public certificates lazily on the first token verification.
    Without warming this cache, the first real /v1/meals/today request can sit pending for many seconds.

    This deliberately verifies an invalid Firebase-shaped token. The expected failure is ignored;
    the useful side effect is initialization of the verifier path and public-cert fetch/cache.
    """
    app = get_firebase_app()
    project_id = getattr(app, 'project_id', None)
    token = _build_unsigned_firebase_like_token(project_id)
    try:
        auth.verify_id_token(token)
    except Exception as exc:  # Expected: invalid signature / unknown kid.
        logger.debug(
            'Firebase auth verifier warmup ended with expected error: %s: %s',
            type(exc).__name__,
            exc,
        )


def _warm_firestore() -> None:
    client = get_firestore_client()
    # Querying a non-critical collection warms credentials, DNS, TLS and the Firestore gRPC channel.
    # The collection does not need to exist.
    stream = client.collection('_calnito_warmup').limit(1).stream()
    next(stream, None)


def _warm_supabase() -> None:
    # create_client() is cached. This warms config parsing/client construction before user traffic.
    get_supabase_client()


def warm_backend_dependencies() -> None:
    started = time.perf_counter()
    logger.info('Backend warmup started')

    _measure_step('firebase_admin', _warm_firebase_admin)
    _measure_step('firebase_auth_verifier', _warm_firebase_auth_verifier)
    _measure_step('firestore', _warm_firestore)
    _measure_step('supabase_client', _warm_supabase)

    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info('Backend warmup finished %.1fms', elapsed_ms)
