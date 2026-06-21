"""用户消息模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {"comment": "用户站内消息与健康提醒表"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="消息主键 ID"
    )
    mini_user_id: Mapped[str] = mapped_column(
        String(100), index=True, comment="微信小程序用户唯一标识"
    )
    title: Mapped[str] = mapped_column(String(200), comment="消息标题")
    content: Mapped[str] = mapped_column(Text, comment="消息正文")
    message_type: Mapped[str] = mapped_column(
        String(30),
        default="system",
        comment="消息类型，如 system、abnormal_pressure、continuous_risk",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        default="info",
        comment="消息风险级别：info、warning、high、critical",
    )
    related_record_id: Mapped[int | None] = mapped_column(
        Integer, comment="关联的血压记录 ID"
    )
    action_type: Mapped[str | None] = mapped_column(
        String(30), comment="消息点击动作类型，如 switch_tab"
    )
    action_path: Mapped[str | None] = mapped_column(
        String(300), comment="消息点击后跳转的小程序页面路径"
    )
    dedupe_key: Mapped[str | None] = mapped_column(
        String(150),
        unique=True,
        index=True,
        comment="自动消息唯一键，用于防止重复提醒",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        comment="是否已读：true=已读，false=未读",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="消息创建时间",
    )
