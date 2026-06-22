"""血压记录增删改查与趋势分析接口。"""

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_mini_user_id
from app.core.database import get_db
from app.models.blood_pressure import BloodPressureRecord
from app.models.message import Message
from app.schemas.blood_pressure import (
    BloodPressureCreate,
    BloodPressureOut,
    BloodPressureUpdate,
)
from app.services.health import classify_pressure, classify_pressure_detail
from app.services.notifications import sync_pressure_notifications

router = APIRouter(prefix="/blood-pressure", tags=["blood-pressure"])


def calculate_overview_stats(
    records: list[BloodPressureRecord],
) -> dict:
    total = len(records)
    normal_count = sum(
        classify_pressure(item.systolic, item.diastolic)[0] == "normal"
        for item in records
    )
    abnormal_count = total - normal_count
    return {
        "total": total,
        "record_days": len({item.created_at.date() for item in records}),
        "normal_count": normal_count,
        "abnormal_count": abnormal_count,
        "normal_rate": (
            round(normal_count / total * 100, 1) if total else 0
        ),
        "abnormal_rate": (
            round(abnormal_count / total * 100, 1) if total else 0
        ),
    }


def calculate_period_stats(
    records: list[BloodPressureRecord],
) -> dict:
    total = len(records)
    normal_count = sum(
        classify_pressure(item.systolic, item.diastolic)[0] == "normal"
        for item in records
    )
    abnormal_count = total - normal_count

    def average(values: list[int]) -> float | None:
        return round(sum(values) / len(values), 1) if values else None

    return {
        "total": total,
        "normal_count": normal_count,
        "abnormal_count": abnormal_count,
        "normal_rate": (
            round(normal_count / total * 100, 1) if total else 0
        ),
        "abnormal_rate": (
            round(abnormal_count / total * 100, 1) if total else 0
        ),
        "avg_systolic": average([item.systolic for item in records]),
        "avg_diastolic": average([item.diastolic for item in records]),
        "avg_heart_rate": average(
            [item.heart_rate for item in records if item.heart_rate]
        ),
    }


def build_single_day_trend_points(
    records: list[BloodPressureRecord],
) -> list[dict]:
    """保留同一天每条测量记录的真实时间位置。"""
    return [
        {
            "label": record.created_at.strftime("%H:%M"),
            "systolic": float(record.systolic),
            "diastolic": float(record.diastolic),
            "heart_rate": (
                float(record.heart_rate)
                if record.heart_rate is not None
                else None
            ),
            "count": 1,
        }
        for record in sorted(records, key=lambda item: item.created_at)
    ]


def serialize_record(record: BloodPressureRecord) -> dict:
    classification = classify_pressure_detail(
        record.systolic, record.diastolic
    )
    return {
        "id": record.id,
        "systolic": record.systolic,
        "diastolic": record.diastolic,
        "heart_rate": record.heart_rate,
        "created_at": record.created_at,
        "note": record.note,
        "status": classification["status"],
        "status_text": classification["status_text"],
        "pressure_category": classification["category"],
        "hypertension_grade": classification["hypertension_grade"],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_record(
    payload: BloodPressureCreate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    classification = classify_pressure_detail(
        payload.systolic, payload.diastolic
    )
    record = BloodPressureRecord(
        systolic=payload.systolic,
        diastolic=payload.diastolic,
        heart_rate=payload.heart_rate,
        hypertension_grade=classification["hypertension_grade"],
        created_at=payload.measured_at or datetime.now(),
        user_id=payload.user_id,
        mini_user_id=mini_user_id,
        mini_user_name=payload.mini_user_name,
        note=payload.note,
    )
    db.add(record)
    db.flush()
    sync_pressure_notifications(db, record)
    db.commit()
    db.refresh(record)
    return {"code": 0, "message": "血压记录保存成功", "data": serialize_record(record)}


@router.get("")
def list_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    start_time: datetime | None = Query(
        default=None,
        description="测量开始时间，精确到秒",
    ),
    end_time: datetime | None = Query(
        default=None,
        description="测量结束时间，精确到秒",
    ),
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=422, detail="开始时间不能晚于结束时间")

    base = select(BloodPressureRecord).where(
        BloodPressureRecord.mini_user_id == mini_user_id
    )
    if start_time:
        base = base.where(BloodPressureRecord.created_at >= start_time)
    if end_time:
        base = base.where(BloodPressureRecord.created_at <= end_time)

    total = db.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0
    records = db.scalars(
        base.order_by(
            BloodPressureRecord.created_at.desc(),
            BloodPressureRecord.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [serialize_record(item) for item in records],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
    }


@router.get("/overview")
def health_archive_overview(
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    """返回健康档案汇总及近十二个月趋势。"""
    records = db.scalars(
        select(BloodPressureRecord)
        .where(BloodPressureRecord.mini_user_id == mini_user_id)
        .order_by(BloodPressureRecord.created_at.desc())
    ).all()
    stats = calculate_overview_stats(records)
    today = datetime.now().date()
    week_start = today - timedelta(days=6)
    recent_7_days_records = [
        item
        for item in records
        if week_start <= item.created_at.date() <= today
    ]
    recent_7_days = calculate_period_stats(recent_7_days_records)
    avg = lambda values: round(sum(values) / len(values), 1) if values else None

    end = datetime.now()
    # 当前自然月加前 11 个自然月，保证页面始终最多展示 12 个月。
    start_month_index = end.year * 12 + end.month - 1 - 11
    start = datetime(
        start_month_index // 12,
        start_month_index % 12 + 1,
        1,
    )
    month_bucket = func.date_trunc("month", BloodPressureRecord.created_at)
    monthly_rows = db.execute(
        select(
            func.to_char(month_bucket, "YYYY-MM").label("month"),
            func.round(func.avg(BloodPressureRecord.systolic), 1),
            func.round(func.avg(BloodPressureRecord.diastolic), 1),
            func.round(func.avg(BloodPressureRecord.heart_rate), 1),
            func.count(BloodPressureRecord.id),
        )
        .where(
            BloodPressureRecord.mini_user_id == mini_user_id,
            BloodPressureRecord.created_at >= start,
            BloodPressureRecord.created_at <= end,
        )
        .group_by(month_bucket)
        .order_by(month_bucket)
    ).all()

    first_record_at = min(
        (item.created_at for item in records),
        default=None,
    )
    latest = serialize_record(records[0]) if records else None
    return {
        "code": 0,
        "message": "success",
        "data": {
            **stats,
            "recent_7_days": recent_7_days,
            "first_record_at": first_record_at,
            "latest": latest,
            "averages": {
                "systolic": avg([item.systolic for item in records]),
                "diastolic": avg([item.diastolic for item in records]),
                "heart_rate": avg(
                    [item.heart_rate for item in records if item.heart_rate]
                ),
            },
            "monthly": [
                {
                    "month": row[0],
                    "systolic": float(row[1]) if row[1] is not None else None,
                    "diastolic": float(row[2]) if row[2] is not None else None,
                    "heart_rate": float(row[3]) if row[3] is not None else None,
                    "count": row[4],
                }
                for row in monthly_rows
            ],
        },
    }


@router.put("/{record_id}")
def update_record(
    record_id: int,
    payload: BloodPressureUpdate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    record = db.scalar(
        select(BloodPressureRecord).where(
            BloodPressureRecord.id == record_id,
            BloodPressureRecord.mini_user_id == mini_user_id,
        )
    )
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, "created_at" if field == "measured_at" else field, value)
    if record.systolic <= record.diastolic:
        raise HTTPException(status_code=422, detail="收缩压必须大于舒张压")
    record.hypertension_grade = classify_pressure_detail(
        record.systolic, record.diastolic
    )["hypertension_grade"]
    db.flush()
    sync_pressure_notifications(db, record)
    db.commit()
    db.refresh(record)
    return {"code": 0, "message": "记录更新成功", "data": serialize_record(record)}


@router.delete("/{record_id}")
def delete_record(
    record_id: int,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    record = db.scalar(
        select(BloodPressureRecord).where(
            BloodPressureRecord.id == record_id,
            BloodPressureRecord.mini_user_id == mini_user_id,
        )
    )
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    related_messages = db.scalars(
        select(Message).where(
            Message.mini_user_id == mini_user_id,
            Message.related_record_id == record_id,
        )
    ).all()
    for message in related_messages:
        db.delete(message)
    db.delete(record)
    db.commit()
    return {"code": 0, "message": "记录已删除", "data": None}


@router.get("/trend")
def trend(
    dimension: Literal["day", "month", "year"] = "month",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    end = end_date or datetime.now()
    start = start_date or (end - timedelta(days=365))
    use_measurement_time_points = (
        dimension == "day" and start.date() == end.date()
    )
    formats = {
        "day": ("day", "YYYY-MM-DD"),
        "month": ("month", "YYYY-MM"),
        "year": ("year", "YYYY"),
    }
    trunc_unit, label_format = formats[dimension]
    bucket = func.date_trunc(trunc_unit, BloodPressureRecord.created_at)
    label = func.to_char(bucket, label_format)
    rows = (
        []
        if use_measurement_time_points
        else db.execute(
            select(
                label.label("label"),
                func.round(func.avg(BloodPressureRecord.systolic), 1),
                func.round(func.avg(BloodPressureRecord.diastolic), 1),
                func.round(func.avg(BloodPressureRecord.heart_rate), 1),
                func.count(BloodPressureRecord.id),
            )
            .where(
                BloodPressureRecord.mini_user_id == mini_user_id,
                BloodPressureRecord.created_at >= start,
                BloodPressureRecord.created_at <= end,
            )
            .group_by(bucket)
            .order_by(bucket)
        )
        .all()
    )
    records = db.scalars(
        select(BloodPressureRecord)
        .where(
            BloodPressureRecord.mini_user_id == mini_user_id,
            BloodPressureRecord.created_at >= start,
            BloodPressureRecord.created_at <= end,
        )
        .order_by(BloodPressureRecord.created_at.desc())
    ).all()
    total = len(records)
    avg = lambda values: round(sum(values) / len(values), 1) if values else None
    abnormal_count = sum(
        classify_pressure(item.systolic, item.diastolic)[0] != "normal"
        for item in records
    )
    grade_order = [
        ("low", "血压偏低"),
        ("normal", "正常血压"),
        ("high_normal", "正常高值"),
        ("grade_1", "高血压1级"),
        ("grade_2", "高血压2级"),
        ("grade_3", "高血压3级"),
    ]
    grade_counts = {key: 0 for key, _ in grade_order}
    for item in records:
        category = classify_pressure_detail(
            item.systolic, item.diastolic
        )["category"]
        grade_counts[category] += 1
    latest_classification = (
        classify_pressure_detail(records[0].systolic, records[0].diastolic)
        if records
        else None
    )
    points = (
        build_single_day_trend_points(records)
        if use_measurement_time_points
        else [
            {
                "label": row[0],
                "systolic": float(row[1]) if row[1] is not None else None,
                "diastolic": float(row[2]) if row[2] is not None else None,
                "heart_rate": float(row[3]) if row[3] is not None else None,
                "count": row[4],
            }
            for row in rows
        ]
    )
    return {
        "code": 0,
        "message": "success",
        "data": {
            "dimension": dimension,
            "granularity": (
                "measurement_time"
                if use_measurement_time_points
                else dimension
            ),
            "start_date": start,
            "end_date": end,
            "points": points,
            "summary": {
                "total": total,
                "avg_systolic": avg([item.systolic for item in records]),
                "avg_diastolic": avg([item.diastolic for item in records]),
                "avg_heart_rate": avg(
                    [item.heart_rate for item in records if item.heart_rate]
                ),
                "abnormal_count": abnormal_count,
                "latest_grade": latest_classification,
                "grade_distribution": [
                    {
                        "category": key,
                        "label": label,
                        "count": grade_counts[key],
                        "percent": round(grade_counts[key] / total * 100, 1)
                        if total
                        else 0,
                    }
                    for key, label in grade_order
                ],
            },
        },
    }
