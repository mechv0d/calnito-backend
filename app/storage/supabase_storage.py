from __future__ import annotations

import logging
import threading
import time
from functools import lru_cache
from urllib.parse import quote
from uuid import uuid4

import httpx
from supabase import Client, create_client

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SignedUrlError(RuntimeError):
    """Raised when a Supabase signed URL cannot be created quickly enough."""


_signed_url_cache: dict[str, tuple[float, str]] = {}
_signed_url_cache_lock = threading.Lock()


@lru_cache
def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_secret_key)


def clear_signed_url_cache() -> None:
    with _signed_url_cache_lock:
        _signed_url_cache.clear()


def _extract_signed_url(response_data: dict) -> str | None:
    value = (
        response_data.get('signedURL')
        or response_data.get('signedUrl')
        or response_data.get('signed_url')
        or response_data.get('data', {}).get('signedURL')
        or response_data.get('data', {}).get('signedUrl')
        or response_data.get('data', {}).get('signed_url')
    )
    return str(value) if value else None


def _absolute_signed_url(supabase_url: str, signed_url: str) -> str:
    if signed_url.startswith('http://') or signed_url.startswith('https://'):
        return signed_url

    base = supabase_url.rstrip('/')
    if signed_url.startswith('/storage/v1/'):
        return f'{base}{signed_url}'
    if signed_url.startswith('/object/'):
        return f'{base}/storage/v1{signed_url}'
    if signed_url.startswith('object/'):
        return f'{base}/storage/v1/{signed_url}'
    if signed_url.startswith('/'):
        return f'{base}{signed_url}'
    return f'{base}/storage/v1/{signed_url}'


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = get_supabase_client()
        self.bucket = self.client.storage.from_(self.settings.supabase_storage_bucket)

    def upload_meal_photo(self, uid: str, meal_id: str, webp_bytes: bytes) -> str:
        path = f'users/{uid}/meals/{meal_id}/{uuid4().hex}.webp'
        self.bucket.upload(
            path,
            webp_bytes,
            file_options={
                'content-type': 'image/webp',
                'upsert': 'false',
            },
        )
        return path

    def create_signed_url(self, path: str | None) -> str | None:
        if not path:
            return None

        cached = self._get_cached_signed_url(path)
        if cached:
            return cached

        signed_url = self._create_signed_url_with_timeout(path)
        if signed_url:
            self._set_cached_signed_url(path, signed_url)
        return signed_url

    def _get_cached_signed_url(self, path: str) -> str | None:
        now = time.monotonic()
        with _signed_url_cache_lock:
            cached = _signed_url_cache.get(path)
            if cached is None:
                return None
            expires_at, signed_url = cached
            if expires_at <= now:
                _signed_url_cache.pop(path, None)
                return None
            return signed_url

    def _set_cached_signed_url(self, path: str, signed_url: str) -> None:
        ttl_seconds = max(1, self.settings.signed_url_cache_seconds)
        expires_at = time.monotonic() + ttl_seconds
        with _signed_url_cache_lock:
            _signed_url_cache[path] = (expires_at, signed_url)

    def _create_signed_url_with_timeout(self, path: str) -> str | None:
        encoded_bucket = quote(self.settings.supabase_storage_bucket, safe='')
        encoded_path = quote(path.lstrip('/'), safe='/')
        url = f'{self.settings.supabase_url}/storage/v1/object/sign/{encoded_bucket}/{encoded_path}'
        headers = {
            'apikey': self.settings.supabase_secret_key,
            'authorization': f'Bearer {self.settings.supabase_secret_key}',
            'content-type': 'application/json',
        }
        timeout = httpx.Timeout(
            timeout=self.settings.supabase_signed_url_timeout_seconds,
            connect=min(self.settings.supabase_signed_url_timeout_seconds, 2.0),
        )

        try:
            with httpx.Client(timeout=timeout, http2=False) as client:
                response = client.post(
                    url,
                    headers=headers,
                    json={'expiresIn': self.settings.signed_url_expires_seconds},
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise SignedUrlError(f'Supabase signed URL request timed out for {path}') from exc
        except httpx.HTTPError as exc:
            raise SignedUrlError(f'Supabase signed URL request failed for {path}: {exc}') from exc

        signed_url = _extract_signed_url(response.json())
        if not signed_url:
            raise SignedUrlError(f'Supabase signed URL response does not contain URL for {path}')
        return _absolute_signed_url(self.settings.supabase_url, signed_url)

    def remove_file(self, path: str | None) -> None:
        if not path:
            return
        with _signed_url_cache_lock:
            _signed_url_cache.pop(path, None)
        self.bucket.remove([path])
