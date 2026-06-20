"""为现有小程序用户生成过去三年的血压趋势测试数据。

默认选择记录数最多的非空 mini_user_id。生成数据带有统一备注标记，
再次运行时会先清理该用户旧的同类测试数据，避免重复叠加。
"""

import argparse
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, func, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.models.blood_pressure import BloodPressureRecord

SEED_MARKER = "[TREND_TEST_3Y]"


def select_target_user(db, requested_user_id: str | None) -> str:
    if requested_user_id:
        return requested_user_id

    user_id = db.scalar(
        select(BloodPressureRecord.mini_user_id)
        .where(BloodPressureRecord.mini_user_id.is_not(None))
        .group_by(BloodPressureRecord.mini_user_id)
        .order_by(func.count(BloodPressureRecord.id).desc())
        .limit(1)
    )
    if not user_id:
        raise RuntimeError("数据库中没有可用的小程序用户，请先录入一条血压记录")
    return user_id


def build_records(user_id: str, end_time: datetime) -> list[BloodPressureRecord]:
    """每三天生成一条数据，形成缓慢变化并混入少量异常波动。"""
    random_generator = random.Random(f"hiothy-{user_id}-three-years")
    start_time = end_time - timedelta(days=365 * 3)
    current = start_time
    records: list[BloodPressureRecord] = []
    index = 0

    while current <= end_time:
        # 年度和月度周期，让折线图具有可观察但不过度跳跃的趋势。
        yearly_wave = math.sin(index / 19) * 5
        monthly_wave = math.sin(index / 5) * 3
        gradual_change = min(index / 120, 3)
        systolic = round(
            121
            + yearly_wave
            + monthly_wave
            + gradual_change
            + random_generator.gauss(0, 4)
        )
        diastolic = round(
            77
            + yearly_wave * 0.45
            + monthly_wave * 0.35
            + random_generator.gauss(0, 3)
        )
        heart_rate = round(
            70
            + math.sin(index / 7) * 5
            + random_generator.gauss(0, 4)
        )

        # 约每两个月制造一次偏高记录，约每半年制造一次明显异常记录。
        category = "常规"
        if index and index % 60 == 0:
            systolic += 35
            diastolic += 22
            heart_rate += 12
            category = "明显偏高"
        elif index and index % 20 == 0:
            systolic += 18
            diastolic += 10
            category = "轻度偏高"

        systolic = max(90, min(190, systolic))
        diastolic = max(55, min(systolic - 10, 120, diastolic))
        heart_rate = max(48, min(125, heart_rate))

        measured_at = current.replace(
            hour=7 if index % 2 == 0 else 20,
            minute=(index * 7) % 60,
            second=(index * 13) % 60,
            microsecond=0,
        )
        if measured_at > end_time:
            measured_at = end_time.replace(microsecond=0)
        records.append(
            BloodPressureRecord(
                systolic=systolic,
                diastolic=diastolic,
                heart_rate=heart_rate,
                created_at=measured_at,
                updated_at=measured_at,
                mini_user_id=user_id,
                note=f"{SEED_MARKER} {category}趋势测试数据",
            )
        )
        current += timedelta(days=3)
        index += 1

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="生成过去三年的血压趋势测试数据")
    parser.add_argument("--user-id", help="指定 mini_user_id；不填则自动选择")
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="只删除该用户由本脚本生成的测试数据",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        user_id = select_target_user(db, args.user_id)
        delete_result = db.execute(
            delete(BloodPressureRecord).where(
                BloodPressureRecord.mini_user_id == user_id,
                BloodPressureRecord.note.like(f"{SEED_MARKER}%"),
            )
        )
        deleted_count = delete_result.rowcount or 0

        if args.clean_only:
            db.commit()
            print(f"已删除用户 {user_id} 的 {deleted_count} 条趋势测试数据。")
            return

        records = build_records(user_id, datetime.now())
        db.add_all(records)
        db.commit()
        print(
            f"用户 {user_id}：清理旧测试数据 {deleted_count} 条，"
            f"新增 {len(records)} 条。"
        )
        print(
            f"时间范围：{records[0].created_at:%Y-%m-%d %H:%M:%S} "
            f"至 {records[-1].created_at:%Y-%m-%d %H:%M:%S}"
        )


if __name__ == "__main__":
    main()
