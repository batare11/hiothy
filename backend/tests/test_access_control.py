from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.access import (
    PermissionDefinition,
    Role,
    RolePermission,
    UserRole,
)
from app.services.access_control import (
    Permission,
    get_access_context,
    require_permission,
)


def create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Role.__table__.create(engine)
    PermissionDefinition.__table__.create(engine)
    RolePermission.__table__.create(engine)
    UserRole.__table__.create(engine)
    return Session(engine)


def seed_rbac(db: Session) -> None:
    db.add_all(
        [
            Role(code="vip", name="普通会员", rank=10),
            Role(code="svip", name="超级会员", rank=20),
            Role(code="admin", name="管理员", rank=100),
            PermissionDefinition(
                code="cloud_ocr",
                name="AI 图片识别",
                module="ocr",
            ),
            PermissionDefinition(
                code="ai_health_report",
                name="AI 档案分析",
                module="archive",
            ),
            PermissionDefinition(
                code="feedback_manage",
                name="反馈管理",
                module="admin",
            ),
            PermissionDefinition(
                code="role_manage",
                name="角色权限管理",
                module="admin",
            ),
        ]
    )
    db.flush()
    db.add_all(
        [
            RolePermission(role_code="vip", permission_code="cloud_ocr"),
            RolePermission(role_code="svip", permission_code="cloud_ocr"),
            RolePermission(
                role_code="svip",
                permission_code="ai_health_report",
            ),
            *[
                RolePermission(
                    role_code="admin",
                    permission_code=permission.value,
                )
                for permission in Permission
            ],
        ]
    )
    db.commit()


def test_role_permission_matrix():
    db = create_session()
    seed_rbac(db)
    assert get_access_context(db, "free-user").permissions == frozenset()

    db.add(UserRole(mini_user_id="vip-user", role_code="vip"))
    db.add(UserRole(mini_user_id="svip-user", role_code="svip"))
    db.add(UserRole(mini_user_id="admin-user", role_code="admin"))
    db.commit()

    vip = get_access_context(db, "vip-user")
    assert vip.allows(Permission.CLOUD_OCR)
    assert not vip.allows(Permission.AI_HEALTH_REPORT)

    svip = get_access_context(db, "svip-user")
    assert svip.allows(Permission.CLOUD_OCR)
    assert svip.allows(Permission.AI_HEALTH_REPORT)
    assert not svip.allows(Permission.FEEDBACK_MANAGE)

    admin = get_access_context(db, "admin-user")
    assert admin.permissions == frozenset(item.value for item in Permission)


def test_permission_denial_uses_403():
    db = create_session()
    seed_rbac(db)
    try:
        require_permission(db, "free-user", Permission.CLOUD_OCR)
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "AI" in exc.detail
    else:
        raise AssertionError("free user must not receive cloud OCR permission")


def test_admin_is_only_granted_by_database_role_binding():
    db = create_session()
    seed_rbac(db)
    assert get_access_context(db, "unbound-user").role == "free"

    db.add(UserRole(mini_user_id="first-admin", role_code="admin"))
    db.add(UserRole(mini_user_id="second-admin", role_code="admin"))
    db.commit()

    assert get_access_context(db, "first-admin").role == "admin"
    assert get_access_context(db, "second-admin").allows(
        Permission.FEEDBACK_MANAGE
    )


def test_disabled_permission_is_not_granted():
    db = create_session()
    seed_rbac(db)
    db.add(UserRole(mini_user_id="vip-user", role_code="vip"))
    permission = db.get(PermissionDefinition, "cloud_ocr")
    permission.enabled = False
    db.commit()
    assert not get_access_context(db, "vip-user").allows(Permission.CLOUD_OCR)


def test_role_permission_binding_is_database_driven():
    db = create_session()
    seed_rbac(db)
    db.add(UserRole(mini_user_id="vip-user", role_code="vip"))
    db.commit()
    assert get_access_context(db, "vip-user").allows(Permission.CLOUD_OCR)

    binding = db.scalar(
        select(RolePermission).where(
            RolePermission.role_code == "vip",
            RolePermission.permission_code == "cloud_ocr",
        )
    )
    db.delete(binding)
    db.commit()
    assert not get_access_context(db, "vip-user").allows(Permission.CLOUD_OCR)
