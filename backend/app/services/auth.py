"""微信 code2Session 与本地访问令牌服务。"""

import base64
import binascii
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

WECHAT_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
logger = logging.getLogger(__name__)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _token_secret() -> bytes:
    if len(settings.auth_token_secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务器登录令牌密钥尚未正确配置",
        )
    return settings.auth_token_secret.encode("utf-8")


def public_user_id(openid: str) -> str:
    """生成可展示给客户端的稳定标识，避免直接返回 openid。"""
    return hashlib.sha256(openid.encode("utf-8")).hexdigest()[:16]


def create_access_token(openid: str) -> tuple[str, int]:
    expires_in = settings.auth_token_expire_days * 24 * 60 * 60
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": openid,
        "iat": now,
        "exp": now + expires_in,
        "iss": settings.app_name,
    }
    encoded_header = _base64url_encode(
        json.dumps(header, separators=(",", ":")).encode()
    )
    encoded_payload = _base64url_encode(
        json.dumps(payload, separators=(",", ":")).encode()
    )
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        _token_secret(), signing_input.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{signing_input}.{_base64url_encode(signature)}", expires_in


def verify_access_token(token: str) -> str:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}"
        expected = hmac.new(
            _token_secret(), signing_input.encode("ascii"), hashlib.sha256
        ).digest()
        supplied = _base64url_decode(encoded_signature)
        if not hmac.compare_digest(expected, supplied):
            raise ValueError("invalid signature")

        header = json.loads(_base64url_decode(encoded_header))
        payload = json.loads(_base64url_decode(encoded_payload))
        if header.get("alg") != "HS256":
            raise ValueError("invalid algorithm")
        if payload.get("iss") != settings.app_name:
            raise ValueError("invalid issuer")
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("expired token")
        openid = payload.get("sub")
        if not isinstance(openid, str) or not openid:
            raise ValueError("invalid subject")
        return openid
    except HTTPException:
        raise
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态无效或已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def exchange_code_for_openid(code: str) -> str:
    if not settings.wechat_app_id or not settings.wechat_app_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务器尚未配置微信登录",
        )

    params = {
        "appid": settings.wechat_app_id,
        "secret": settings.wechat_app_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        timeout = httpx.Timeout(15, connect=10)
        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(
            timeout=timeout,
            transport=transport,
            trust_env=False,
        ) as client:
            response = await client.get(WECHAT_CODE2SESSION_URL, params=params)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "Wechat code2Session request failed: %s: %s",
            type(exc).__name__,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"连接微信登录服务失败（{type(exc).__name__}），请稍后重试",
        ) from exc

    openid = data.get("openid")
    if not openid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                f"微信登录失败（{data.get('errcode', 'unknown')}）："
                f"{data.get('errmsg', 'unknown error')}"
            ),
        )
    return str(openid)
