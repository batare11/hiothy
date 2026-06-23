"""集中式角色权限服务，业务模块只依赖权限编码。"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.access import (
    PermissionDefinition,
    Role,
    RolePermission,
    UserRole,
)


class Permission(str, Enum):
    CLOUD_OCR = "cloud_ocr"
    AI_HEALTH_REPORT = "ai_health_report"
    FEEDBACK_MANAGE = "feedback_manage"
    ROLE_MANAGE = "role_manage"


@dataclass(frozen=True)
class AccessContext:
    role: str
    role_name: str
    roles: tuple[str, ...]
    permissions: frozenset[str]

    def allows(self, permission: Permission | str) -> bool:
        value = permission.value if isinstance(permission, Permission) else permission
        return value in self.permissions


def get_access_context(db: Session, mini_user_id: str) -> AccessContext:
    now = datetime.now()
    roles = tuple(
        db.scalars(
            select(Role)
            .join(UserRole, UserRole.role_code == Role.code)
            .where(
                UserRole.mini_user_id == mini_user_id,
                Role.enabled.is_(True),
                or_(
                    UserRole.expires_at.is_(None),
                    UserRole.expires_at > now,
                ),
            )
        ).all()
    )
    if not roles:
        return AccessContext(
            role="free",
            role_name="免费用户",
            roles=(),
            permissions=frozenset(),
        )
    role_codes = tuple(role.code for role in roles)
    primary_role = max(roles, key=lambda role: role.rank)
    permissions = set(
        db.scalars(
            select(PermissionDefinition.code)
            .join(
                RolePermission,
                RolePermission.permission_code == PermissionDefinition.code,
            )
            .where(
                RolePermission.role_code.in_(role_codes),
                PermissionDefinition.enabled.is_(True),
            )
            .distinct()
        ).all()
    )
    return AccessContext(
        role=primary_role.code,
        role_name=primary_role.name,
        roles=role_codes,
        permissions=frozenset(permissions),
    )


def require_permission(
    db: Session,
    mini_user_id: str,
    permission: Permission,
) -> AccessContext:
    access = get_access_context(db, mini_user_id)
    if access.allows(permission):
        return access
    messages = {
        Permission.CLOUD_OCR: "仅拥有 AI 智能图片识别权限的用户可以使用该功能",
        Permission.AI_HEALTH_REPORT: "仅拥有 AI 档案分析权限的用户可以使用该功能",
        Permission.FEEDBACK_MANAGE: "仅管理员可以管理反馈",
        Permission.ROLE_MANAGE: "仅管理员可以管理会员角色",
    }
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=messages[permission],
    )
