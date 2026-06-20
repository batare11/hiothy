"""API 公共依赖。"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth import verify_access_token

bearer_scheme = HTTPBearer(auto_error=True)


def get_mini_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """从后端签发的 Bearer Token 中取得可信微信 openid。"""
    return verify_access_token(credentials.credentials)
