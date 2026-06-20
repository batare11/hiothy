"""微信登录请求结构。"""

from pydantic import BaseModel, Field


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)
