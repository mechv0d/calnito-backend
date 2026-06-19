import pytest
from fastapi import HTTPException

import app.auth.dependencies as deps
from app.auth.dependencies import get_current_user


@pytest.mark.asyncio
async def test_get_current_user_requires_bearer_token():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(None)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_verifies_firebase_token(monkeypatch):
    monkeypatch.setattr(deps, "get_firebase_app", lambda: object())
    monkeypatch.setattr(
        deps.auth,
        "verify_id_token",
        lambda token, check_revoked=False: {"uid": "u1", "email": "u1@example.com"},
    )

    user = await get_current_user("Bearer good-token")

    assert user.uid == "u1"
    assert user.email == "u1@example.com"
