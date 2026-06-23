"""管理员反馈与会员角色管理接口。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_mini_user_id
from app.core.database import get_db
from app.models.access import (
    PermissionDefinition,
    Role,
    RolePermission,
    UserRole,
)
from app.models.feedback import Feedback
from app.models.user_profile import UserProfile
from app.schemas.user import (
    FeedbackReply,
    PermissionCreate,
    PermissionUpdate,
    RoleCreate,
    RoleUpdate,
    UserRoleUpdate,
)
from app.services.access_control import Permission, require_permission
from app.services.auth import public_user_id

router = APIRouter(prefix="/admin", tags=["admin"])
ROLE_MANAGE_CODE = Permission.ROLE_MANAGE.value


def count_enabled_role_manage_bindings(
    db: Session,
    exclude_role_code: str | None = None,
) -> int:
    query = (
        select(func.count())
        .select_from(RolePermission)
        .join(Role, Role.code == RolePermission.role_code)
        .where(
            RolePermission.permission_code == ROLE_MANAGE_CODE,
            Role.enabled.is_(True),
        )
    )
    if exclude_role_code:
        query = query.where(RolePermission.role_code != exclude_role_code)
    return db.scalar(query) or 0


def serialize_role(role: Role, permission_codes: list[str]) -> dict:
    return {
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "rank": role.rank,
        "enabled": role.enabled,
        "permission_codes": permission_codes,
        "created_at": role.created_at,
    }


def serialize_permission(permission: PermissionDefinition) -> dict:
    return {
        "code": permission.code,
        "name": permission.name,
        "description": permission.description,
        "module": permission.module,
        "enabled": permission.enabled,
        "created_at": permission.created_at,
    }


@router.get("/rbac")
def get_rbac_configuration(
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(db, mini_user_id, Permission.ROLE_MANAGE)
    roles = db.scalars(
        select(Role).order_by(Role.rank.desc(), Role.code)
    ).all()
    bindings = db.execute(
        select(RolePermission.role_code, RolePermission.permission_code)
    ).all()
    permission_map: dict[str, list[str]] = {}
    for role_code, permission_code in bindings:
        permission_map.setdefault(role_code, []).append(permission_code)
    permissions = db.scalars(
        select(PermissionDefinition).order_by(
            PermissionDefinition.module,
            PermissionDefinition.code,
        )
    ).all()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "roles": [
                serialize_role(role, permission_map.get(role.code, []))
                for role in roles
            ],
            "permissions": [
                serialize_permission(permission) for permission in permissions
            ],
        },
    }


@router.post("/roles")
def create_role(
    payload: RoleCreate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(db, mini_user_id, Permission.ROLE_MANAGE)
    role = Role(**payload.model_dump())
    db.add(role)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="角色编码已存在") from exc
    db.refresh(role)
    return {
        "code": 0,
        "message": "角色创建成功",
        "data": serialize_role(role, []),
    }


@router.put("/roles/{role_code}")
def update_role(
    role_code: str,
    payload: RoleUpdate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(db, mini_user_id, Permission.ROLE_MANAGE)
    role = db.get(Role, role_code)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if (
        role.enabled
        and not payload.enabled
        and db.scalar(
            select(RolePermission.id).where(
                RolePermission.role_code == role_code,
                RolePermission.permission_code == ROLE_MANAGE_CODE,
            )
        )
        and count_enabled_role_manage_bindings(db, role_code) == 0
    ):
        raise HTTPException(
            status_code=400,
            detail="至少需要保留一个启用角色拥有角色管理权限",
        )
    for field, value in payload.model_dump().items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    permission_codes = list(
        db.scalars(
            select(RolePermission.permission_code).where(
                RolePermission.role_code == role_code
            )
        ).all()
    )
    return {
        "code": 0,
        "message": "角色更新成功",
        "data": serialize_role(role, permission_codes),
    }


@router.post("/permissions")
def create_permission(
    payload: PermissionCreate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(db, mini_user_id, Permission.ROLE_MANAGE)
    permission = PermissionDefinition(**payload.model_dump())
    db.add(permission)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="功能权限编码已存在") from exc
    db.refresh(permission)
    return {
        "code": 0,
        "message": "功能权限创建成功",
        "data": serialize_permission(permission),
    }


@router.put("/permissions/{permission_code}")
def update_permission(
    permission_code: str,
    payload: PermissionUpdate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(db, mini_user_id, Permission.ROLE_MANAGE)
    permission = db.get(PermissionDefinition, permission_code)
    if permission is None:
        raise HTTPException(status_code=404, detail="功能权限不存在")
    if permission_code == ROLE_MANAGE_CODE and not payload.enabled:
        raise HTTPException(
            status_code=400,
            detail="角色管理权限不能停用，否则管理后台将无法继续授权",
        )
    for field, value in payload.model_dump().items():
        setattr(permission, field, value)
    db.commit()
    db.refresh(permission)
    return {
        "code": 0,
        "message": "功能权限更新成功",
        "data": serialize_permission(permission),
    }


@router.put("/roles/{role_code}/permissions/{permission_code}")
def bind_role_permission(
    role_code: str,
    permission_code: str,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(db, mini_user_id, Permission.ROLE_MANAGE)
    if db.get(Role, role_code) is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if db.get(PermissionDefinition, permission_code) is None:
        raise HTTPException(status_code=404, detail="功能权限不存在")
    exists = db.scalar(
        select(RolePermission.id).where(
            RolePermission.role_code == role_code,
            RolePermission.permission_code == permission_code,
        )
    )
    if exists is None:
        db.add(
            RolePermission(
                role_code=role_code,
                permission_code=permission_code,
            )
        )
        db.commit()
    return {"code": 0, "message": "权限绑定成功", "data": None}


@router.delete("/roles/{role_code}/permissions/{permission_code}")
def unbind_role_permission(
    role_code: str,
    permission_code: str,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(db, mini_user_id, Permission.ROLE_MANAGE)
    binding_exists = db.scalar(
        select(RolePermission.id).where(
            RolePermission.role_code == role_code,
            RolePermission.permission_code == permission_code,
        )
    )
    if (
        binding_exists is not None
        and permission_code == ROLE_MANAGE_CODE
        and count_enabled_role_manage_bindings(db) <= 1
    ):
        raise HTTPException(
            status_code=400,
            detail="至少需要保留一个启用角色拥有角色管理权限",
        )
    db.execute(
        delete(RolePermission).where(
            RolePermission.role_code == role_code,
            RolePermission.permission_code == permission_code,
        )
    )
    db.commit()
    return {"code": 0, "message": "权限解绑成功", "data": None}


def serialize_admin_feedback(
    feedback: Feedback,
    nickname: str | None = None,
) -> dict:
    return {
        "id": feedback.id,
        "user_id": public_user_id(feedback.mini_user_id)[-12:],
        "nickname": nickname or "微信用户",
        "content": feedback.content,
        "status": feedback.status,
        "reply": feedback.reply,
        "replied_at": feedback.replied_at,
        "created_at": feedback.created_at,
    }


@router.get("/feedback")
def list_all_feedback(
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending|processing|resolved)$",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(db, mini_user_id, Permission.FEEDBACK_MANAGE)
    filters = []
    if status_filter:
        filters.append(Feedback.status == status_filter)
    total = db.scalar(
        select(func.count()).select_from(Feedback).where(*filters)
    ) or 0
    rows = db.execute(
        select(Feedback, UserProfile.nickname)
        .outerjoin(
            UserProfile,
            UserProfile.mini_user_id == Feedback.mini_user_id,
        )
        .where(*filters)
        .order_by(Feedback.created_at.desc(), Feedback.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [
                serialize_admin_feedback(feedback, nickname)
                for feedback, nickname in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
    }


@router.put("/feedback/{feedback_id}/reply")
def reply_feedback(
    feedback_id: int,
    payload: FeedbackReply,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(db, mini_user_id, Permission.FEEDBACK_MANAGE)
    feedback = db.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="反馈不存在")
    feedback.reply = payload.reply.strip()
    feedback.replied_by = mini_user_id
    feedback.replied_at = datetime.now()
    feedback.status = "resolved"
    db.commit()
    db.refresh(feedback)
    return {
        "code": 0,
        "message": "回复成功",
        "data": serialize_admin_feedback(feedback),
    }


def find_user_by_archive_id(db: Session, archive_id: str) -> str:
    profiles = db.scalars(select(UserProfile)).all()
    for profile in profiles:
        if public_user_id(profile.mini_user_id)[-12:] == archive_id:
            return profile.mini_user_id
    raise HTTPException(status_code=404, detail="未找到该健康档案用户")


@router.put("/users/{archive_id}/role")
def update_user_role(
    archive_id: str,
    payload: UserRoleUpdate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(db, mini_user_id, Permission.ROLE_MANAGE)
    target_user_id = find_user_by_archive_id(db, archive_id)
    role = db.get(Role, payload.role)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if not role.enabled:
        raise HTTPException(status_code=400, detail="该角色已停用")
    existing = db.scalar(
        select(UserRole).where(
            UserRole.mini_user_id == target_user_id,
            UserRole.role_code == payload.role,
        )
    )
    if existing:
        existing.expires_at = payload.expires_at
    else:
        db.add(
            UserRole(
                mini_user_id=target_user_id,
                role_code=payload.role,
                expires_at=payload.expires_at,
            )
        )
    db.commit()
    return {
        "code": 0,
        "message": "角色设置成功",
        "data": {
            "user_id": archive_id,
            "role": payload.role,
            "expires_at": payload.expires_at,
        },
    }
