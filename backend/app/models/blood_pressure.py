"""血压记录模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BloodPressureRecord(Base):
    __tablename__ = "bp_records"
    __table_args__ = {"comment": "血压测量记录表"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="血压记录主键 ID"
    )
    systolic: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="收缩压（高压），单位：mmHg"
    )
    diastolic: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="舒张压（低压），单位：mmHg"
    )
    heart_rate: Mapped[int | None] = mapped_column(
        Integer, comment="心率，单位：次/分"
    )
    hypertension_grade: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        comment="成人诊室血压高血压等级：0=未达到高血压，1=1级，2=2级，3=3级",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="测量时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="记录最后更新时间",
    )
    user_id: Mapped[str | None] = mapped_column(
        String(50), comment="业务用户 ID（兼容字段）"
    )
    mini_user_id: Mapped[str | None] = mapped_column(
        String(100), index=True, comment="微信小程序用户唯一标识"
    )
    mini_user_name: Mapped[str | None] = mapped_column(
        String(100), comment="测量用户名称"
    )
    note: Mapped[str | None] = mapped_column(
        Text, comment="测量备注，如熬夜、服药、症状等"
    )
