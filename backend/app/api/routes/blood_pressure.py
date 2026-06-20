"""血压记录增删改查与趋势分析接口。"""

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_mini_user_id
from app.core.database import get_db
from app.models.blood_pressure import BloodPressureRecord
from app.schemas.blood_pressure import (
    BloodPressureCreate,
    BloodPressureOut,
    BloodPressureUpdate,
)
from app.services.health import classify_pressure

router = APIRouter(prefix="/blood-pressure", tags=["blood-pressure"])


def serialize_record(record: BloodPressureRecord) -> dict:
    pressure_status, status_text = classify_pressure(
        record.systolic, record.diastolic
    )
    return {
        "id": record.id,
        "systolic": record.systolic,
        "diastolic": record.diastolic,
        "heart_rate": record.heart_rate,
        "created_at": record.created_at,
        "note": record.note,
        "status": pressure_status,
        "status_text": status_text,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_record(
    payload: BloodPressureCreate,
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    record = BloodPressureRecord(
        systolic=payload.systolic,
        diastolic=payload.diastolic,
        heart_rate=payload.heart_rate,
        created_at=payload.measured_at or datetime.now(),
        user_id=payload.user_id,
        mini_user_id=mini_user_id,
        mini_user_name=payload.mini_user_name,
        note=payload.note,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"code": 0, "message": "血压记录保存成功", "data": serialize_record(record)}


@router.get("")
def list_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    base = select(BloodPressureRecord).where(
        BloodPressureRecord.mini_user_id == mini_user_id
    )
    total = db.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0
    records = db.scalars(
        base.order_by(BloodPressureRecord.created_at.desc())
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
    formats = {
        "day": ("day", "YYYY-MM-DD"),
        "month": ("month", "YYYY-MM"),
        "year": ("year", "YYYY"),
    }
    trunc_unit, label_format = formats[dimension]
    bucket = func.date_trunc(trunc_unit, BloodPressureRecord.created_at)
    label = func.to_char(bucket, label_format)
    rows = db.execute(
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
    ).all()
    records = db.scalars(
        select(BloodPressureRecord).where(
            BloodPressureRecord.mini_user_id == mini_user_id,
            BloodPressureRecord.created_at >= start,
            BloodPressureRecord.created_at <= end,
        )
    ).all()
    total = len(records)
    avg = lambda values: round(sum(values) / len(values), 1) if values else None
    abnormal_count = sum(
        classify_pressure(item.systolic, item.diastolic)[0] != "normal"
        for item in records
    )
    return {
        "code": 0,
        "message": "success",
        "data": {
            "dimension": dimension,
            "start_date": start,
            "end_date": end,
            "points": [
                {
                    "label": row[0],
                    "systolic": float(row[1]) if row[1] is not None else None,
                    "diastolic": float(row[2]) if row[2] is not None else None,
                    "heart_rate": float(row[3]) if row[3] is not None else None,
                    "count": row[4],
                }
                for row in rows
            ],
            "summary": {
                "total": total,
                "avg_systolic": avg([item.systolic for item in records]),
                "avg_diastolic": avg([item.diastolic for item in records]),
                "avg_heart_rate": avg(
                    [item.heart_rate for item in records if item.heart_rate]
                ),
                "abnormal_count": abnormal_count,
            },
        },
    }
