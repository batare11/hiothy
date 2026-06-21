"""根据血压记录生成站内健康提醒。"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.blood_pressure import BloodPressureRecord
from app.models.message import Message
from app.services.health import classify_pressure_detail


@dataclass(frozen=True)
class AlertPayload:
    title: str
    content: str
    severity: str
    message_type: str


def build_pressure_alert(record: BloodPressureRecord) -> AlertPayload | None:
    result = classify_pressure_detail(record.systolic, record.diastolic)
    reading = f"{record.systolic}/{record.diastolic} mmHg"
    category = result["category"]
    if category == "low":
        return AlertPayload(
            title="血压偏低提醒",
            content=f"本次血压为 {reading}。如伴有头晕、乏力或晕厥，请及时就医。",
            severity="warning",
            message_type="abnormal_pressure",
        )
    if category == "grade_1":
        return AlertPayload(
            title="血压偏高提醒",
            content=(
                f"本次血压为 {reading}，达到{result['status_text']}范围。"
                "建议静坐后规范复测，并持续记录。"
            ),
            severity="warning",
            message_type="abnormal_pressure",
        )
    if category == "grade_2":
        return AlertPayload(
            title="血压明显偏高",
            content=(
                f"本次血压为 {reading}，达到{result['status_text']}范围。"
                "建议近期规律复测，并咨询专业医生。"
            ),
            severity="high",
            message_type="abnormal_pressure",
        )
    if category == "grade_3":
        return AlertPayload(
            title="血压严重偏高",
            content=(
                f"本次血压为 {reading}，达到{result['status_text']}范围。"
                "请立即安静休息后复测；如伴胸痛、呼吸困难、剧烈头痛或肢体异常，请及时就医。"
            ),
            severity="critical",
            message_type="abnormal_pressure",
        )
    return None


def _upsert_message(
    db: Session,
    *,
    mini_user_id: str,
    dedupe_key: str,
    payload: AlertPayload,
    related_record_id: int,
) -> None:
    message = db.scalar(
        select(Message).where(Message.dedupe_key == dedupe_key)
    )
    if message is None:
        message = Message(
            mini_user_id=mini_user_id,
            dedupe_key=dedupe_key,
            related_record_id=related_record_id,
        )
        db.add(message)
    message.title = payload.title
    message.content = payload.content
    message.severity = payload.severity
    message.message_type = payload.message_type
    message.action_type = "switch_tab"
    message.action_path = "/pages/analysis/index"


def sync_pressure_notifications(
    db: Session,
    record: BloodPressureRecord,
) -> None:
    """同步单次异常提醒，并在连续三次高血压时生成趋势提醒。"""
    if not record.id or not record.mini_user_id:
        return

    dedupe_key = f"pressure:{record.mini_user_id}:{record.id}"
    alert = build_pressure_alert(record)
    existing = db.scalar(
        select(Message).where(Message.dedupe_key == dedupe_key)
    )
    if alert:
        _upsert_message(
            db,
            mini_user_id=record.mini_user_id,
            dedupe_key=dedupe_key,
            payload=alert,
            related_record_id=record.id,
        )
    elif existing:
        db.delete(existing)

    recent = db.scalars(
        select(BloodPressureRecord)
        .where(BloodPressureRecord.mini_user_id == record.mini_user_id)
        .order_by(
            BloodPressureRecord.created_at.desc(),
            BloodPressureRecord.id.desc(),
        )
        .limit(3)
    ).all()
    if len(recent) < 3:
        return
    grades = [
        classify_pressure_detail(item.systolic, item.diastolic)[
            "hypertension_grade"
        ]
        for item in recent
    ]
    if all(grade >= 1 for grade in grades):
        highest_grade = max(grades)
        payload = AlertPayload(
            title="连续血压偏高提醒",
            content=(
                "最近连续 3 次记录均达到高血压范围，"
                f"其中最高为高血压{highest_grade}级。"
                "建议保持规范测量并携带记录咨询专业医生。"
            ),
            severity="critical" if highest_grade >= 3 else "high",
            message_type="continuous_risk",
        )
        _upsert_message(
            db,
            mini_user_id=record.mini_user_id,
            dedupe_key=f"continuous:{record.mini_user_id}:{record.id}",
            payload=payload,
            related_record_id=record.id,
        )
    else:
        continuous_message = db.scalar(
            select(Message).where(
                Message.dedupe_key
                == f"continuous:{record.mini_user_id}:{record.id}"
            )
        )
        if continuous_message:
            db.delete(continuous_message)
