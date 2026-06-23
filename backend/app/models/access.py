"""角色与用户角色绑定模型。"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"comment": "系统角色定义表"}

    code: Mapped[str] = mapped_column(
        String(30), primary_key=True, comment="角色编码，如 vip、svip、admin"
    )
    name: Mapped[str] = mapped_column(String(50), comment="角色名称")
    description: Mapped[str | None] = mapped_column(
        String(300), comment="角色能力说明"
    )
    rank: Mapped[int] = mapped_column(
        Integer, default=0, comment="角色展示优先级，数值越大优先级越高"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="角色是否启用"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="角色创建时间",
    )


class PermissionDefinition(Base):
    __tablename__ = "permissions"
    __table_args__ = {"comment": "系统功能权限定义表"}

    code: Mapped[str] = mapped_column(
        String(60), primary_key=True, comment="功能权限编码"
    )
    name: Mapped[str] = mapped_column(String(80), comment="功能权限名称")
    description: Mapped[str | None] = mapped_column(
        String(300), comment="功能权限说明"
    )
    module: Mapped[str] = mapped_column(
        String(50), default="general", comment="权限所属功能模块"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="功能权限是否启用"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="功能权限创建时间",
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint(
            "role_code",
            "permission_code",
            name="uq_role_permissions_role_permission",
        ),
        {"comment": "角色与功能权限绑定表"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="角色权限绑定主键 ID"
    )
    role_code: Mapped[str] = mapped_column(
        ForeignKey("roles.code", ondelete="CASCADE"),
        index=True,
        comment="角色编码",
    )
    permission_code: Mapped[str] = mapped_column(
        ForeignKey("permissions.code", ondelete="CASCADE"),
        index=True,
        comment="功能权限编码",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="角色权限绑定时间",
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint(
            "mini_user_id",
            "role_code",
            name="uq_user_roles_user_role",
        ),
        {"comment": "小程序用户与角色绑定表"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="用户角色绑定主键 ID"
    )
    mini_user_id: Mapped[str] = mapped_column(
        String(100), index=True, comment="微信小程序用户唯一标识"
    )
    role_code: Mapped[str] = mapped_column(
        ForeignKey("roles.code"),
        index=True,
        comment="绑定的角色编码",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="角色到期时间；为空表示长期有效"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="角色绑定时间",
    )
