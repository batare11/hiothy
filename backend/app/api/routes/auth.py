"""微信小程序登录接口。"""

from fastapi import APIRouter

from app.schemas.auth import WechatLoginRequest
from app.services.auth import (
    create_access_token,
    exchange_code_for_openid,
    public_user_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/wechat-login")
async def wechat_login(payload: WechatLoginRequest) -> dict:
    openid = await exchange_code_for_openid(payload.code)
    access_token, expires_in = create_access_token(openid)
    return {
        "code": 0,
        "message": "登录成功",
        "data": {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "user_id": public_user_id(openid),
        },
    }
