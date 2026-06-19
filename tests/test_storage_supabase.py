from types import SimpleNamespace

import app.storage.supabase_storage as storage_module
from app.storage.supabase_storage import StorageService


class FakeBucket:
    def __init__(self, signed_response):
        self.signed_response = signed_response
        self.uploads = []
        self.removed = []

    def upload(self, path, data, file_options=None):
        self.uploads.append((path, data, file_options))
        return {"path": path}

    def create_signed_url(self, path, expires):
        self.last_signed_args = (path, expires)
        return self.signed_response

    def remove(self, paths):
        self.removed.append(paths)


def make_service(bucket):
    service = object.__new__(StorageService)
    service.settings = SimpleNamespace(
        supabase_storage_bucket="meal-photos",
        signed_url_expires_seconds=777,
    )
    service.bucket = bucket
    return service


def test_create_signed_url_accepts_supabase_dict_formats():
    bucket = FakeBucket({"data": {"signedUrl": "https://signed"}})
    service = make_service(bucket)

    assert service.create_signed_url("a/b.webp") == "https://signed"
    assert bucket.last_signed_args == ("a/b.webp", 777)


def test_create_signed_url_accepts_object_formats():
    bucket = FakeBucket(SimpleNamespace(signed_url="https://object-signed"))
    service = make_service(bucket)

    assert service.create_signed_url("a/b.webp") == "https://object-signed"


def test_upload_meal_photo_uses_webp_content_type(monkeypatch):
    bucket = FakeBucket({"signedURL": "https://signed"})
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
    bucket = FakeBucket({})
    service = make_service(bucket)

    service.remove_file(None)
    service.remove_file("")
    assert bucket.removed == []

    service.remove_file("a/b.webp")
    assert bucket.removed == [["a/b.webp"]]
