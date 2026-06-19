import pytest
from fastapi import HTTPException

import app.users.service as users_module
from app.users.service import UserService


class FakeSnapshot:
    def __init__(self, exists, data=None):
        self.exists = exists
        self._data = data or {}

    def to_dict(self):
        return self._data


class FakeUserDoc:
    def __init__(self, exists=False, data=None):
        self.exists = exists
        self.data = data or {}
        self.set_calls = []

    def get(self):
        return FakeSnapshot(self.exists, self.data)

    def set(self, data, merge=False):
        self.set_calls.append((data, merge))
        self.data = {**self.data, **data} if merge else data
        self.exists = True


def test_get_or_create_profile_returns_existing(monkeypatch, frozen_dt):
    doc = FakeUserDoc(exists=True, data={"email": "stored@example.com", "timezone": "Europe/Helsinki"})
    monkeypatch.setattr(users_module, "user_doc", lambda uid: doc)

    result = UserService().get_or_create_profile("u1", "token@example.com")

    assert result["email"] == "stored@example.com"
    assert result["timezone"] == "Europe/Helsinki"
    assert doc.set_calls == []


def test_get_or_create_profile_creates_missing(monkeypatch, frozen_dt):
    doc = FakeUserDoc(exists=False)
    monkeypatch.setattr(users_module, "user_doc", lambda uid: doc)
    monkeypatch.setattr(users_module, "now_utc", lambda: frozen_dt)

    result = UserService().get_or_create_profile("u1", "u1@example.com")

    assert result["uid"] == "u1"
    assert result["email"] == "u1@example.com"
    assert doc.set_calls[0][0]["created_at"] == frozen_dt


def test_update_profile_rejects_invalid_timezone(monkeypatch):
    monkeypatch.setattr(users_module, "user_doc", lambda uid: FakeUserDoc())

    with pytest.raises(HTTPException) as exc:
        UserService().update_profile("u1", "u1@example.com", "Bad/Timezone")

    assert exc.value.status_code == 400


def test_update_profile_sets_timezone(monkeypatch, frozen_dt):
    doc = FakeUserDoc(exists=False)
    monkeypatch.setattr(users_module, "user_doc", lambda uid: doc)
    monkeypatch.setattr(users_module, "now_utc", lambda: frozen_dt)

    result = UserService().update_profile("u1", "u1@example.com", "Europe/Helsinki")

    assert doc.set_calls[0][0]["timezone"] == "Europe/Helsinki"
    assert doc.set_calls[0][1] is True
    assert result["timezone"] == "Europe/Helsinki"
