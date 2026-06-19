from functools import lru_cache
from uuid import uuid4

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_secret_key)


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

        response = self.bucket.create_signed_url(
            path,
            self.settings.signed_url_expires_seconds,
        )

        if isinstance(response, dict):
            return (
                response.get('signedURL')
                or response.get('signedUrl')
                or response.get('signed_url')
                or response.get('data', {}).get('signedURL')
                or response.get('data', {}).get('signedUrl')
            )

        for attr in ('signed_url', 'signedURL', 'signedUrl'):
            value = getattr(response, attr, None)
            if value:
                return value

        data = getattr(response, 'data', None)
        if isinstance(data, dict):
            return data.get('signedURL') or data.get('signedUrl') or data.get('signed_url')

        return None

    def remove_file(self, path: str | None) -> None:
        if not path:
            return
        self.bucket.remove([path])
