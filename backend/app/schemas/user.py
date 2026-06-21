"""用户、消息及反馈结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageOut(BaseModel):
    id: int
    title: str
    content: str
    message_type: str
    severity: str
    related_record_id: int | None
    action_type: str | None
    action_path: str | None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    nickname: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)
    gender: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    birth_date: str | None = Field(default=None, max_length=20)


class UserProfileOut(BaseModel):
    mini_user_id: str
    nickname: str
    avatar_url: str | None
    gender: str | None
    phone: str | None
    birth_date: str | None

    model_config = ConfigDict(from_attributes=True)


class HealthArchiveUpdate(BaseModel):
    age: int | None = Field(default=None, ge=0, le=150)
    height_cm: float | None = Field(default=None, ge=50, le=250)
    weight_jin: float | None = Field(default=None, ge=20, le=500)
    gender: int | None = Field(default=None, ge=0, le=1)
    marital_status: int | None = Field(default=None, ge=0, le=1)
    smoking: bool = False
    drinking: bool = False
    staying_up_late: bool = False
    note: str | None = Field(default=None, max_length=1000)


class FeedbackCreate(BaseModel):
    content: str = Field(min_length=2, max_length=2000)
    contact: str | None = Field(default=None, max_length=100)


class FeedbackOut(BaseModel):
    id: int
    content: str
    contact: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
