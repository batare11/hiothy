"""集中导出模型，确保 SQLAlchemy 能发现所有表。"""

from app.models.blood_pressure import BloodPressureRecord
from app.models.feedback import Feedback
from app.models.message import Message
from app.models.user_profile import UserProfile

__all__ = ["BloodPressureRecord", "Feedback", "Message", "UserProfile"]

