from types import SimpleNamespace

import pytest

import app.storage.supabase_storage as storage_module
from app.storage.supabase_storage import SignedUrlError, StorageService, clear_signed_url_cache


class FakeBucket:
    def __init__(self):
        self.uploads = []
        self.removed = []

    def upload(self, path, data, file_options=None):
        self.uploads.append((path, data, file_options))
        return {"path": path}

    def remove(self, paths):
        self.removed.append(paths)


def make_service(bucket=None):
    service = object.__new__(StorageService)
    service.settings = SimpleNamespace(
        supabase_url="https://example.supabase.co",
        supabase_secret_key="sb_secret_test",
        supabase_storage_bucket="meal-photos",
        signed_url_expires_seconds=777,
        supabase_signed_url_timeout_seconds=3.0,
        signed_url_cache_seconds=900,
    )
    service.bucket = bucket or FakeBucket()
    clear_signed_url_cache()
    return service


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class FakeHttpxClient:
    requests = []
    response_data = {"signedURL": "/object/sign/meal-photos/a/b.webp?token=abc"}

    def __init__(self, timeout=None, http2=None):
        self.timeout = timeout
        self.http2 = http2

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, headers=None, json=None):
        self.__class__.requests.append((url, headers, json, self.timeout, self.http2))
        return FakeResponse(self.__class__.response_data)


def test_create_signed_url_uses_direct_supabase_request_and_timeout(monkeypatch):
    FakeHttpxClient.requests = []
    FakeHttpxClient.response_data = {"signedURL": "/object/sign/meal-photos/a/b.webp?token=abc"}
    monkeypatch.setattr(storage_module.httpx, "Client", FakeHttpxClient)
    service = make_service()

    signed_url = service.create_signed_url("a/b.webp")

    assert signed_url == "https://example.supabase.co/storage/v1/object/sign/meal-photos/a/b.webp?token=abc"
    url, headers, body, timeout, http2 = FakeHttpxClient.requests[0]
    assert url == "https://example.supabase.co/storage/v1/object/sign/meal-photos/a/b.webp"
    assert headers["apikey"] == "sb_secret_test"
    assert headers["authorization"] == "Bearer sb_secret_test"
    assert body == {"expiresIn": 777}
    assert http2 is False


def test_create_signed_url_caches_result(monkeypatch):
    FakeHttpxClient.requests = []
    FakeHttpxClient.response_data = {"signedURL": "https://signed.example/a/b.webp"}
    monkeypatch.setattr(storage_module.httpx, "Client", FakeHttpxClient)
    service = make_service()

    assert service.create_signed_url("a/b.webp") == "https://signed.example/a/b.webp"
    assert service.create_signed_url("a/b.webp") == "https://signed.example/a/b.webp"

    assert len(FakeHttpxClient.requests) == 1


def test_create_signed_url_wraps_timeout(monkeypatch):
    class TimeoutHttpxClient(FakeHttpxClient):
        def post(self, url, headers=None, json=None):
            raise storage_module.httpx.ReadTimeout("timed out")

    monkeypatch.setattr(storage_module.httpx, "Client", TimeoutHttpxClient)
    service = make_service()

    with pytest.raises(SignedUrlError):
        service.create_signed_url("a/b.webp")


def test_upload_meal_photo_uses_webp_content_type(monkeypatch):
    bucket = FakeBucket()
    service = make_service(bucket)
    monkeypatch.setattr(storage_module, "uuid4", lambda: SimpleNamespace(hex="abc123"))

    path = service.upload_meal_photo("u1", "m1", b"webp")

    assert path == "users/u1/meals/m1/abc123.webp"
    assert bucket.uploads == [
        (
            "users/u1/meals/m1/abc123.webp",
            b"webp",
            {"content-type": "image/webp", "upsert": "false"},
        )
    ]


def test_remove_file_is_noop_for_empty_path():
    bucket = FakeBucket()
    service = make_service(bucket)

    service.remove_file(None)
    service.remove_file("")
    assert bucket.removed == []

    service.remove_file("a/b.webp")
    assert bucket.removed == [["a/b.webp"]]
