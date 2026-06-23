"""意见反馈模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
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
    reply_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="管理员回复逻辑删除时间"
    )
    reply_deleted_by: Mapped[str | None] = mapped_column(
        String(100), comment="撤销回复的管理员用户唯一标识"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="反馈逻辑删除时间"
    )
    deleted_by: Mapped[str | None] = mapped_column(
        String(100), comment="删除反馈的管理员用户唯一标识"
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="会话最后活动时间",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="反馈提交时间",
    )


class FeedbackMessage(Base):
    __tablename__ = "feedback_messages"
    __table_args__ = (
        UniqueConstraint("legacy_key", name="uq_feedback_messages_legacy_key"),
        {"comment": "反馈会话消息表"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="反馈消息主键 ID"
    )
    feedback_id: Mapped[int] = mapped_column(
        ForeignKey("feedback.id", ondelete="CASCADE"),
        index=True,
        comment="所属反馈会话 ID",
    )
    sender_type: Mapped[str] = mapped_column(
        String(20), comment="发送方类型：user 或 admin"
    )
    sender_id: Mapped[str] = mapped_column(
        String(100), comment="发送方微信小程序用户唯一标识"
    )
    content: Mapped[str] = mapped_column(Text, comment="消息内容")
    legacy_key: Mapped[str | None] = mapped_column(
        String(100), unique=True, comment="旧字段迁移唯一键"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="消息发送时间",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="消息逻辑删除时间"
    )
    deleted_by: Mapped[str | None] = mapped_column(
        String(100), comment="删除消息的管理员用户唯一标识"
    )
