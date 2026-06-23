"""意见反馈模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = {"comment": "用户意见反馈表"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="反馈主键 ID"
    )
    mini_user_id: Mapped[str] = mapped_column(
        String(100), index=True, comment="微信小程序用户唯一标识"
    )
    content: Mapped[str] = mapped_column(Text, comment="反馈内容")
    contact: Mapped[str | None] = mapped_column(
        String(100), comment="用户联系方式"
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        comment="处理状态，如 pending、processing、resolved",
    )
    reply: Mapped[str | None] = mapped_column(
        Text, comment="管理员回复内容"
    )
    replied_by: Mapped[str | None] = mapped_column(
        String(100), comment="回复管理员的微信小程序用户唯一标识"
    )
    replied_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="管理员回复时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="反馈提交时间",
    )
