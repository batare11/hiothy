"""个人资料和意见反馈接口。"""

import logging
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.dependencies import get_mini_user_id
from app.core.database import get_db
from app.models.feedback import Feedback, FeedbackMessage
from app.models.blood_pressure import BloodPressureRecord
from app.models.health_archive import HealthArchive
from app.models.user_profile import UserProfile
from app.schemas.user import (
    FeedbackCreate,
    FeedbackMessageCreate,
    HealthArchiveUpdate,
    UserProfileUpdate,
)
from app.services.auth import public_user_id
from app.services.access_control import Permission, require_permission
from app.services.health_report import (
    DEEPSEEK_HEALTH_MODEL,
    generate_health_report,
)

router = APIRouter(tags=["users"])
logger = logging.getLogger("uvicorn.error")


def serialize_feedback_messages(
    db: Session,
    feedback: Feedback,
) -> list[dict]:
    messages = db.scalars(
        select(FeedbackMessage)
        .where(
            FeedbackMessage.feedback_id == feedback.id,
            FeedbackMessage.deleted_at.is_(None),
        )
        .order_by(FeedbackMessage.created_at, FeedbackMessage.id)
    ).all()
    if messages:
        return [
            {
                "id": message.id,
                "sender_type": message.sender_type,
                "content": message.content,
                "created_at": message.created_at,
                "can_delete": message.sender_type == "user",
            }
            for message in messages
        ]

    legacy_messages = [
        {
            "id": f"legacy-user-{feedback.id}",
            "sender_type": "user",
            "content": feedback.content,
            "created_at": feedback.created_at,
            "can_delete": False,
        }
    ]
    if feedback.reply and feedback.reply_deleted_at is None:
        legacy_messages.append(
            {
                "id": f"legacy-admin-{feedback.id}",
                "sender_type": "admin",
                "content": feedback.reply,
                "created_at": feedback.replied_at or feedback.created_at,
                "can_delete": False,
            }
        )
    return legacy_messages


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
    require_permission(db, mini_user_id, Permission.AI_HEALTH_REPORT)
    trace_id = uuid.uuid4().hex[:10]
    started_at = time.perf_counter()
    logger.info("AI health report [%s] request received", trace_id)
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
        logger.warning(
            "AI health report [%s] rejected: missing archive fields=%s",
            trace_id,
            ",".join(missing_fields),
        )
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
    logger.info(
        "AI health report [%s] data loaded: records=%d elapsed=%.2fs",
        trace_id,
        len(records),
        time.perf_counter() - started_at,
    )
    report = await generate_health_report(archive, records, trace_id)
    logger.info(
        "AI health report [%s] response ready: total_elapsed=%.2fs",
        trace_id,
        time.perf_counter() - started_at,
    )
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
    )
    db.add(feedback)
    db.flush()
    db.add(
        FeedbackMessage(
            feedback_id=feedback.id,
            sender_type="user",
            sender_id=mini_user_id,
            content=payload.content,
        )
    )
    feedback.last_activity_at = datetime.now()
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


@router.post("/feedback/{feedback_id}/messages")
def create_feedback_message(
    feedback_id: int,
    payload: FeedbackMessageCreate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    feedback = db.get(Feedback, feedback_id)
    if (
        feedback is None
        or feedback.deleted_at is not None
        or feedback.mini_user_id != mini_user_id
    ):
        raise HTTPException(status_code=404, detail="反馈不存在")
    message = FeedbackMessage(
        feedback_id=feedback.id,
        sender_type="user",
        sender_id=mini_user_id,
        content=payload.content.strip(),
    )
    db.add(message)
    feedback.status = "pending"
    feedback.last_activity_at = datetime.now()
    db.commit()
    db.refresh(message)
    return {
        "code": 0,
        "message": "消息已发送",
        "data": {
            "id": message.id,
            "sender_type": message.sender_type,
            "content": message.content,
            "created_at": message.created_at,
        },
    }


@router.delete("/feedback/{feedback_id}/messages/{message_id}")
def delete_feedback_message(
    feedback_id: int,
    message_id: int,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    feedback = db.get(Feedback, feedback_id)
    if (
        feedback is None
        or feedback.deleted_at is not None
        or feedback.mini_user_id != mini_user_id
    ):
        raise HTTPException(status_code=404, detail="反馈不存在")
    message = db.get(FeedbackMessage, message_id)
    if (
        message is None
        or message.feedback_id != feedback_id
        or message.sender_type != "user"
        or message.sender_id != mini_user_id
        or message.deleted_at is not None
    ):
        raise HTTPException(status_code=404, detail="消息不存在")
    message.deleted_at = datetime.now()
    message.deleted_by = mini_user_id
    feedback.last_activity_at = datetime.now()
    db.commit()
    return {"code": 0, "message": "消息已删除", "data": None}


@router.delete("/feedback/{feedback_id}")
def delete_feedback(
    feedback_id: int,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    feedback = db.get(Feedback, feedback_id)
    if (
        feedback is None
        or feedback.deleted_at is not None
        or feedback.mini_user_id != mini_user_id
    ):
        raise HTTPException(status_code=404, detail="反馈不存在")
    feedback.deleted_at = datetime.now()
    feedback.deleted_by = mini_user_id
    db.execute(
        update(FeedbackMessage)
        .where(
            FeedbackMessage.feedback_id == feedback_id,
            FeedbackMessage.deleted_at.is_(None),
        )
        .values(
            deleted_at=feedback.deleted_at,
            deleted_by=mini_user_id,
        )
    )
    db.commit()
    return {"code": 0, "message": "反馈已删除", "data": None}


@router.get("/feedback")
def list_feedback(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    base = select(Feedback).where(
        Feedback.mini_user_id == mini_user_id,
        Feedback.deleted_at.is_(None),
    )
    total = db.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0
    items = db.scalars(
        base.order_by(Feedback.last_activity_at.desc(), Feedback.id.desc())
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
                    "status": item.status,
                    "reply": (
                        item.reply if item.reply_deleted_at is None else None
                    ),
                    "replied_at": (
                        item.replied_at
                        if item.reply_deleted_at is None
                        else None
                    ),
                    "messages": serialize_feedback_messages(db, item),
                    "last_activity_at": item.last_activity_at,
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
