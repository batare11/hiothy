"""小程序用户资料模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = {"comment": "微信小程序用户基础资料表"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="用户资料主键 ID"
    )
    mini_user_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        comment="微信小程序用户唯一标识",
    )
    nickname: Mapped[str] = mapped_column(
        String(100), default="微信用户", comment="用户昵称"
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500), comment="用户头像地址"
    )
    gender: Mapped[str | None] = mapped_column(
        String(20), comment="用户性别文字值"
    )
    phone: Mapped[str | None] = mapped_column(
        String(30), comment="用户手机号"
    )
    birth_date: Mapped[str | None] = mapped_column(
        String(20), comment="出生日期，格式：YYYY-MM-DD"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="资料创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="资料最后更新时间",
    )
