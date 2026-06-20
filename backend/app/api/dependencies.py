"""API 公共依赖。"""

from fastapi import Header


def get_mini_user_id(
    x_mini_user_id: str = Header(default="demo-user", max_length=100),
) -> str:
    """开发期从请求头识别用户；上线后应替换为微信 code2Session 鉴权。"""
    return x_mini_user_id

