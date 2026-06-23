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
    birth_date: str | None = Field(default=None, max_length=20)

    model_config = ConfigDict(extra="forbid")


class UserProfileOut(BaseModel):
    mini_user_id: str
    nickname: str
    avatar_url: str | None
    gender: str | None
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

    model_config = ConfigDict(extra="forbid")


class FeedbackOut(BaseModel):
    id: int
    content: str
    status: str
    reply: str | None
    replied_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackReply(BaseModel):
    reply: str = Field(min_length=2, max_length=2000)


class UserRoleUpdate(BaseModel):
    role: str = Field(min_length=2, max_length=30, pattern="^[a-z][a-z0-9_]*$")
    expires_at: datetime | None = None


class RoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30, pattern="^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=300)
    rank: int = Field(default=0, ge=0, le=10000)
    enabled: bool = True


class RoleUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=300)
    rank: int = Field(default=0, ge=0, le=10000)
    enabled: bool = True


class PermissionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60, pattern="^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    module: str = Field(default="general", min_length=1, max_length=50)
    enabled: bool = True


class PermissionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    module: str = Field(default="general", min_length=1, max_length=50)
    enabled: bool = True
