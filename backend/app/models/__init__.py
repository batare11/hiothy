"""集中导出模型，确保 SQLAlchemy 能发现所有表。"""

from app.models.access import (
    PermissionDefinition,
    Role,
    RolePermission,
    UserRole,
)
from app.models.blood_pressure import BloodPressureRecord
from app.models.feedback import Feedback
from app.models.health_archive import HealthArchive
from app.models.message import Message
from app.models.user_profile import UserProfile

__all__ = [
    "BloodPressureRecord",
    "Feedback",
    "HealthArchive",
    "Message",
    "UserProfile",
    "Role",
    "PermissionDefinition",
    "RolePermission",
    "UserRole",
]
