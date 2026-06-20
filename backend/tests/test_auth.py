import asyncio
import time

import pytest
from fastapi import HTTPException

from app.api.routes import auth as auth_route
from app.core.config import settings
from app.schemas.auth import WechatLoginRequest
from app.services.auth import (
    create_access_token,
    public_user_id,
    verify_access_token,
)


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch):
    monkeypatch.setattr(settings, "auth_token_secret", "a" * 64)
    monkeypatch.setattr(settings, "auth_token_expire_days", 30)


def test_access_token_round_trip():
    token, expires_in = create_access_token("openid-test-user")
    assert expires_in == 30 * 24 * 60 * 60
    assert verify_access_token(token) == "openid-test-user"


def test_access_token_rejects_tampering():
    token, _ = create_access_token("openid-test-user")
    header, payload, signature = token.split(".")
    replacement = "a" if payload[0] != "a" else "b"
    tampered = f"{header}.{replacement}{payload[1:]}.{signature}"
    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(tampered)
    assert exc_info.value.status_code == 401


def test_access_token_rejects_expired_token(monkeypatch):
    monkeypatch.setattr(settings, "auth_token_expire_days", 0)
    token, _ = create_access_token("openid-test-user")
    now = int(time.time())
    monkeypatch.setattr(time, "time", lambda: now + 1)
    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token)
    assert exc_info.value.status_code == 401


def test_public_user_id_is_stable_and_does_not_expose_openid():
    first = public_user_id("openid-test-user")
    second = public_user_id("openid-test-user")
    assert first == second
    assert len(first) == 16
    assert "openid" not in first


def test_wechat_login_returns_signed_token_without_exposing_openid(monkeypatch):
    async def fake_exchange(_: str) -> str:
        return "openid-test-user"

    monkeypatch.setattr(auth_route, "exchange_code_for_openid", fake_exchange)
    response = asyncio.run(
        auth_route.wechat_login(WechatLoginRequest(code="test-code"))
    )
    data = response["data"]
    assert verify_access_token(data["access_token"]) == "openid-test-user"
    assert data["user_id"] == public_user_id("openid-test-user")
    assert "openid-test-user" not in data["user_id"]
