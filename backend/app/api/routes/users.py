"""个人资料和意见反馈接口。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_mini_user_id
from app.core.database import get_db
from app.models.feedback import Feedback
from app.models.blood_pressure import BloodPressureRecord
from app.models.health_archive import HealthArchive
from app.models.user_profile import UserProfile
from app.schemas.user import FeedbackCreate, HealthArchiveUpdate, UserProfileUpdate
from app.services.auth import public_user_id
from app.services.health_report import (
    DEEPSEEK_HEALTH_MODEL,
    generate_health_report,
)

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


def get_or_create_health_archive(
    db: Session, mini_user_id: str
) -> HealthArchive:
    archive = db.scalar(
        select(HealthArchive).where(HealthArchive.mini_user_id == mini_user_id)
    )
    if archive:
        return archive
    archive = HealthArchive(mini_user_id=mini_user_id)
    db.add(archive)
    db.commit()
    db.refresh(archive)
    return archive


def serialize_health_archive(archive: HealthArchive) -> dict:
    return {
        "age": archive.age,
        "height_cm": archive.height_cm,
        "weight_jin": archive.weight_jin,
        "gender": archive.gender,
        "marital_status": archive.marital_status,
        "smoking": archive.smoking,
        "drinking": archive.drinking,
        "staying_up_late": archive.staying_up_late,
        "note": archive.note,
        "updated_at": archive.updated_at,
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


@router.get("/health-archive")
def get_health_archive(
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    archive = get_or_create_health_archive(db, mini_user_id)
    return {
        "code": 0,
        "message": "success",
        "data": serialize_health_archive(archive),
    }


@router.put("/health-archive")
def update_health_archive(
    payload: HealthArchiveUpdate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    archive = get_or_create_health_archive(db, mini_user_id)
    for field, value in payload.model_dump().items():
        setattr(archive, field, value)
    db.commit()
    db.refresh(archive)
    return {
        "code": 0,
        "message": "辅助档案保存成功",
        "data": serialize_health_archive(archive),
    }


@router.post("/health-archive/ai-report")
async def create_health_archive_ai_report(
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    archive = get_or_create_health_archive(db, mini_user_id)
    required_fields = {
        "年龄": archive.age,
        "身高": archive.height_cm,
        "体重": archive.weight_jin,
        "性别": archive.gender,
        "婚姻状态": archive.marital_status,
    }
    missing_fields = [
        label for label, value in required_fields.items() if value is None
    ]
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=(
                f"请先补充并保存{ '、'.join(missing_fields) }"
                "后再生成 AI 健康报告"
            ),
        )
    records = db.scalars(
        select(BloodPressureRecord)
        .where(BloodPressureRecord.mini_user_id == mini_user_id)
        .order_by(BloodPressureRecord.created_at.asc())
    ).all()
    report = await generate_health_report(archive, records)
    return {
        "code": 0,
        "message": "AI 健康报告生成成功",
        "data": {
            "model": DEEPSEEK_HEALTH_MODEL,
            "report": report,
            "record_count": len(records),
        },
    }


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


@router.get("/feedback")
def list_feedback(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    base = select(Feedback).where(Feedback.mini_user_id == mini_user_id)
    total = db.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0
    items = db.scalars(
        base.order_by(Feedback.created_at.desc(), Feedback.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [
                {
                    "id": item.id,
                    "content": item.content,
                    "contact": item.contact,
                    "status": item.status,
                    "created_at": item.created_at,
                }
                for item in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
    }
