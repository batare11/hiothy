"""个人资料和意见反馈接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_mini_user_id
from app.core.database import get_db
from app.models.feedback import Feedback
from app.models.user_profile import UserProfile
from app.schemas.user import FeedbackCreate, UserProfileUpdate
from app.services.auth import public_user_id

router = APIRouter(tags=["users"])


def get_or_create_profile(db: Session, mini_user_id: str) -> UserProfile:
    profile = db.scalar(
        select(UserProfile).where(UserProfile.mini_user_id == mini_user_id)
    )
    if profile:
        return profile
    profile = UserProfile(mini_user_id=mini_user_id, nickname="微信用户")
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def serialize_profile(profile: UserProfile) -> dict:
    return {
        "mini_user_id": public_user_id(profile.mini_user_id),
        "nickname": profile.nickname,
        "avatar_url": profile.avatar_url,
        "gender": profile.gender,
        "phone": profile.phone,
        "birth_date": profile.birth_date,
    }


@router.get("/profile")
def get_profile(
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    profile = get_or_create_profile(db, mini_user_id)
    return {"code": 0, "message": "success", "data": serialize_profile(profile)}


@router.put("/profile")
def update_profile(
    payload: UserProfileUpdate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    profile = get_or_create_profile(db, mini_user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return {"code": 0, "message": "资料保存成功", "data": serialize_profile(profile)}


@router.post("/feedback")
def create_feedback(
    payload: FeedbackCreate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    feedback = Feedback(
        mini_user_id=mini_user_id,
        content=payload.content,
        contact=payload.contact,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return {
        "code": 0,
        "message": "感谢反馈，我们会认真处理",
        "data": {
            "id": feedback.id,
            "status": feedback.status,
            "created_at": feedback.created_at,
        },
    }
