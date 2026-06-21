"""消息中心接口。"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_mini_user_id
from app.core.database import get_db
from app.models.message import Message

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("")
def list_messages(
    state: Literal["all", "unread", "read"] = Query(default="all"),
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    query = select(Message).where(Message.mini_user_id == mini_user_id)
    if state == "unread":
        query = query.where(Message.is_read.is_(False))
    elif state == "read":
        query = query.where(Message.is_read.is_(True))
    messages = db.scalars(query.order_by(Message.created_at.desc()).limit(100)).all()
    return {
        "code": 0,
        "message": "success",
        "data": [
            {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "message_type": item.message_type,
                "severity": item.severity,
                "related_record_id": item.related_record_id,
                "action_type": item.action_type,
                "action_path": item.action_path,
                "is_read": item.is_read,
                "created_at": item.created_at,
            }
            for item in messages
        ],
    }


@router.get("/unread-count")
def unread_count(
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    count = db.scalar(
        select(func.count(Message.id)).where(
            Message.mini_user_id == mini_user_id,
            Message.is_read.is_(False),
        )
    ) or 0
    return {"code": 0, "message": "success", "data": {"count": count}}


@router.put("/{message_id}/read")
def mark_as_read(
    message_id: int,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    message = db.scalar(
        select(Message).where(
            Message.id == message_id, Message.mini_user_id == mini_user_id
        )
    )
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    message.is_read = True
    db.commit()
    return {"code": 0, "message": "已标记为已读", "data": None}
