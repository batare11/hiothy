"""当前用户会员身份与权限查询。"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_mini_user_id
from app.core.database import get_db
from app.models.access import PermissionDefinition, Role, RolePermission
from app.services.access_control import get_access_context

router = APIRouter(prefix="/access", tags=["access"])


@router.get("/me")
def get_my_access(
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    access = get_access_context(db, mini_user_id)
    roles = db.scalars(
        select(Role)
        .where(Role.enabled.is_(True))
        .order_by(Role.rank, Role.code)
    ).all()
    bindings = db.execute(
        select(
            RolePermission.role_code,
            PermissionDefinition.code,
            PermissionDefinition.name,
        )
        .join(
            PermissionDefinition,
            PermissionDefinition.code == RolePermission.permission_code,
        )
        .where(PermissionDefinition.enabled.is_(True))
    ).all()
    role_permissions: dict[str, list[dict[str, str]]] = {}
    for role_code, permission_code, permission_name in bindings:
        role_permissions.setdefault(role_code, []).append(
            {"code": permission_code, "name": permission_name}
        )
    available_roles = [
        {
            "code": role.code,
            "name": role.name,
            "description": role.description,
            "permissions": role_permissions.get(role.code, []),
        }
        for role in roles
        if "role_manage"
        not in {
            item["code"] for item in role_permissions.get(role.code, [])
        }
    ]
    return {
        "code": 0,
        "message": "success",
        "data": {
            "role": access.role,
            "role_name": access.role_name,
            "roles": list(access.roles),
            "permissions": sorted(access.permissions),
            "is_admin": access.allows("role_manage"),
            "available_roles": available_roles,
        },
    }
