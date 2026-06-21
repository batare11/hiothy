"""用户辅助健康档案模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HealthArchive(Base):
    __tablename__ = "health_archives"
    __table_args__ = {"comment": "用户辅助健康档案表"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="辅助健康档案主键 ID"
    )
    mini_user_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        comment="微信小程序用户唯一标识",
    )
    age: Mapped[int | None] = mapped_column(Integer, comment="年龄，单位：岁")
    height_cm: Mapped[float | None] = mapped_column(
        Float, comment="身高，单位：厘米"
    )
    weight_jin: Mapped[float | None] = mapped_column(
        Float, comment="体重，单位：斤"
    )
    gender: Mapped[int | None] = mapped_column(
        Integer, comment="性别：1=男，0=女"
    )
    marital_status: Mapped[int | None] = mapped_column(
        Integer, comment="婚姻状态：1=已婚，0=未婚"
    )
    smoking: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否抽烟：true=是，false=否",
    )
    drinking: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否喝酒：true=是，false=否",
    )
    staying_up_late: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否经常熬夜：true=是，false=否",
    )
    note: Mapped[str | None] = mapped_column(
        Text, comment="辅助备注，如慢性病、过敏史、长期服药及近期症状"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="档案创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="档案最后更新时间",
    )
