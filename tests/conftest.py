"""Shared test setup.

The unit test suite must not talk to real Firebase, Firestore, Supabase or an LLM.
This file provides safe defaults and tiny SDK stubs so the tests run on a clean
Windows machine before real cloud credentials are configured.
"""

from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest


# Required by pydantic-settings when app.core.config.get_settings() is used.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("CORS_ORIGINS", "*")
os.environ.setdefault("DEFAULT_TIMEZONE", "UTC")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "sb_secret_test")
os.environ.setdefault("SUPABASE_STORAGE_BUCKET", "meal-photos")
os.environ.setdefault("SIGNED_URL_EXPIRES_SECONDS", "3600")
os.environ.setdefault("SUPABASE_SIGNED_URL_TIMEOUT_SECONDS", "3")
os.environ.setdefault("SIGNED_URL_CACHE_SECONDS", "900")
os.environ.setdefault("LLM_API_KEY", "test-llm-key")
os.environ.setdefault("LLM_MODEL", "test-food-model")
os.environ.setdefault("LLM_RECOMMENDATION_MODEL", "test-recommendation-model")
os.environ.setdefault("LLM_TIMEOUT_SECONDS", "1")
os.environ.setdefault("LLM_MAX_RETRIES", "1")
os.environ.setdefault("MAX_UPLOAD_BYTES", "10485760")
os.environ.setdefault("MAX_IMAGE_SIDE_PX", "1200")
os.environ.setdefault("WEBP_QUALITY", "75")
os.environ.setdefault("USER_FACING_AI_ERROR", "Мы проебались, Босс.")


def _install_firebase_stub() -> None:
    if "firebase_admin" in sys.modules:
        return

    firebase_admin = types.ModuleType("firebase_admin")
    firebase_admin._apps = {}

    class App:  # noqa: D401 - tiny fake object
        """Fake Firebase app."""

    def initialize_app(cred: Any = None, options: dict | None = None) -> App:
        app = App()
        firebase_admin._apps["[DEFAULT]"] = app
        return app

    def get_app() -> App:
        return firebase_admin._apps.setdefault("[DEFAULT]", App())

    firebase_admin.App = App
    firebase_admin.initialize_app = initialize_app
    firebase_admin.get_app = get_app

    auth = types.ModuleType("firebase_admin.auth")

    def verify_id_token(token: str, check_revoked: bool = False) -> dict:
        if token == "bad-token":
            raise ValueError("invalid token")
        return {"uid": "test-user", "email": "boss@example.com"}

    auth.verify_id_token = verify_id_token

    credentials = types.ModuleType("firebase_admin.credentials")

    class Certificate:
        def __init__(self, value: Any) -> None:
            self.value = value

    class ApplicationDefault:
        pass

    credentials.Certificate = Certificate
    credentials.ApplicationDefault = ApplicationDefault

    firestore_mod = types.ModuleType("firebase_admin.firestore")

    class FakeFirebaseFirestoreClient:
        pass

    def client() -> FakeFirebaseFirestoreClient:
        return FakeFirebaseFirestoreClient()

    firestore_mod.client = client

    firebase_admin.auth = auth
    firebase_admin.credentials = credentials
    firebase_admin.firestore = firestore_mod

    sys.modules["firebase_admin"] = firebase_admin
    sys.modules["firebase_admin.auth"] = auth
    sys.modules["firebase_admin.credentials"] = credentials
    sys.modules["firebase_admin.firestore"] = firestore_mod


def _install_google_firestore_stub() -> None:
    if "google.cloud.firestore_v1.base_query" in sys.modules:
        return

    google = sys.modules.setdefault("google", types.ModuleType("google"))
    cloud = sys.modules.setdefault("google.cloud", types.ModuleType("google.cloud"))

    firestore = types.ModuleType("google.cloud.firestore")

    class Query:
        DESCENDING = "DESCENDING"

    firestore.Query = Query

    firestore_v1 = types.ModuleType("google.cloud.firestore_v1")
    base_query = types.ModuleType("google.cloud.firestore_v1.base_query")

    @dataclass(frozen=True)
    class FieldFilter:
        field_path: str
        op_string: str
        value: Any

    base_query.FieldFilter = FieldFilter
    firestore_v1.base_query = base_query
    cloud.firestore = firestore
    google.cloud = cloud

    sys.modules["google.cloud.firestore"] = firestore
    sys.modules["google.cloud.firestore_v1"] = firestore_v1
    sys.modules["google.cloud.firestore_v1.base_query"] = base_query


def _install_supabase_stub() -> None:
    if "supabase" in sys.modules:
        return

    supabase = types.ModuleType("supabase")

    class FakeBucket:
        def __init__(self) -> None:
            self.uploads: list[tuple] = []
            self.removed: list[list[str]] = []

        def upload(self, path: str, data: bytes, file_options: dict | None = None) -> dict:
            self.uploads.append((path, data, file_options))
            return {"path": path}

        def create_signed_url(self, path: str, expires_in: int) -> dict:
            return {"signedURL": f"https://signed.example/{path}?expires={expires_in}"}

        def remove(self, paths: list[str]) -> dict:
            self.removed.append(paths)
            return {"removed": paths}

    class FakeStorage:
        def __init__(self) -> None:
            self.bucket = FakeBucket()

        def from_(self, bucket_name: str) -> FakeBucket:
            return self.bucket

    class Client:
        def __init__(self) -> None:
            self.storage = FakeStorage()

    def create_client(url: str, key: str) -> Client:
        return Client()

    supabase.Client = Client
    supabase.create_client = create_client
    sys.modules["supabase"] = supabase



def _install_openai_stub() -> None:
    if "openai" in sys.modules:
        return

    openai = types.ModuleType("openai")

    class OpenAI:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(
                    create=lambda **call_kwargs: (_ for _ in ()).throw(RuntimeError("OpenAI stub was called without monkeypatch"))
                )
            )

    openai.OpenAI = OpenAI
    sys.modules["openai"] = openai

_install_firebase_stub()
_install_google_firestore_stub()
_install_supabase_stub()
_install_openai_stub()


@pytest.fixture(autouse=True)
def clear_cached_settings_and_clients(monkeypatch: pytest.MonkeyPatch):
    """Each test starts with fresh settings and no cached cloud clients."""
    from app.core.config import get_settings
    from app.core.firebase import get_firebase_app, get_firestore_client
    from app.storage.supabase_storage import clear_signed_url_cache, get_supabase_client

    get_settings.cache_clear()
    get_firebase_app.cache_clear()
    get_firestore_client.cache_clear()
    get_supabase_client.cache_clear()
    clear_signed_url_cache()
    yield
    get_settings.cache_clear()
    get_firebase_app.cache_clear()
    get_firestore_client.cache_clear()
    get_supabase_client.cache_clear()
    clear_signed_url_cache()


@pytest.fixture
def frozen_dt() -> datetime:
    return datetime(2026, 6, 19, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_meal(frozen_dt: datetime) -> dict:
    return {
        "id": "meal-1",
        "uid": "user-1",
        "description": "омлет и хлеб",
        "meal_type": "breakfast",
        "date_local": "2026-06-19",
        "consumed_at": frozen_dt,
        "created_at": frozen_dt,
        "updated_at": frozen_dt,
        "photo": {
            "storage_path": "users/user-1/meals/meal-1/photo.webp",
            "width": 1200,
            "height": 800,
        },
        "items": [
            {
                "product_name": "омлет",
                "portion_g": 180,
                "kcal_per_100g": 154,
                "calories": 277.2,
                "confidence": 0.9,
            }
        ],
        "totals": {"calories": 277.2, "products_count": 1, "total_weight_g": 180},
    }


class DummyStorage:
    def __init__(self) -> None:
        self.removed: list[str | None] = []
        self.uploaded: list[tuple[str, str, bytes]] = []

    def create_signed_url(self, path: str | None) -> str | None:
        if not path:
            return None
        return f"https://signed.test/{path}"

    def upload_meal_photo(self, uid: str, meal_id: str, webp_bytes: bytes) -> str:
        self.uploaded.append((uid, meal_id, webp_bytes))
        return f"users/{uid}/meals/{meal_id}/photo.webp"

    def remove_file(self, path: str | None) -> None:
        self.removed.append(path)


@pytest.fixture
def dummy_storage() -> DummyStorage:
    return DummyStorage()
