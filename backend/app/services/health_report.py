"""使用 DeepSeek V4 Pro 生成健康档案分析报告。"""

import json
import logging
import time
from datetime import datetime

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.blood_pressure import BloodPressureRecord
from app.models.health_archive import HealthArchive
from app.services.health import classify_pressure_detail

logger = logging.getLogger("uvicorn.error")

DEEPSEEK_HEALTH_MODEL = "deepseek-v4-pro"
AI_REPORT_UNAVAILABLE_MESSAGE = "AI 健康分析暂不可用，请稍后重试"
AI_REPORT_TIMEOUT_MESSAGE = "AI 健康分析响应超时，请稍后重试"
AI_REPORT_CONNECTION_MESSAGE = "暂时无法连接 AI 健康分析服务，请稍后重试"

SYSTEM_PROMPT = """你是一名严谨的健康数据归纳助手。
请完整阅读用户使用小程序期间的全部历史测量数据和个人档案，生成一份便于医生快速了解该人员整体情况的中文健康数据报告。

必须遵守：
1. 必须分析输入中的全部 blood_pressure_records，不得只分析最近一次或抽取少量记录。
2. 清楚说明数据覆盖的起止时间、记录总数、记录频率和数据完整性。
3. 分别总结收缩压、舒张压和心率的整体水平、波动、异常频率、阶段变化及测量时段特点。
4. 综合基础档案中的年龄、性别、身高、体重、BMI、BMI 等级、吸烟、饮酒和熬夜情况。
5. 逐条阅读所有测量备注，归纳其中的服药、漏服或服药后测量、熬夜、睡眠、饮食、情绪压力、头晕头痛胸闷心悸等身体表现。
6. 对备注因素与同期血压、心率变化进行谨慎对照，只能表述为“记录中同时出现”“可能相关”或“值得关注”，不能认定因果关系。
7. 对最近 7 天、较早阶段和全部历史进行对照，指出趋势是否稳定、改善、升高或波动，但数据不足时必须明确说明。
8. 只陈述输入数据能够支持的事实和观察，不虚构疾病、症状、用药名称、剂量或检查结果。
9. 不做医学诊断，不指导用户自行停药、换药或调整剂量。
10. 报告面向医生阅读，避免空泛鼓励语，优先给出有数据依据的总体结论、异常模式和备注线索。
11. 如果存在明显严重异常或备注中出现危险症状，应提示及时就医。

使用以下固定结构：

【数据范围与完整性】
【基础档案与 BMI】
【血压总体情况】
【心率总体情况】
【最近7天与历史对比】
【生活习惯与备注线索】
【需要医生重点关注】
【总结】
【重要说明】

“重要说明”必须写明：本报告由 AI 根据用户在小程序中的历史记录生成，仅用于帮助医生和用户了解记录期间的整体情况，不作为医疗诊断、处方或用药调整依据。"""


def calculate_bmi_profile(
    height_cm: float | None,
    weight_jin: float | None,
) -> dict:
    if not height_cm or not weight_jin:
        return {"value": None, "category": "资料不足"}
    bmi = weight_jin / 2 / ((height_cm / 100) ** 2)
    if bmi < 18.5:
        category = "偏瘦"
    elif bmi < 24:
        category = "正常"
    elif bmi < 28:
        category = "超重"
    else:
        category = "肥胖"
    return {"value": round(bmi, 1), "category": category}


def build_health_report_payload(
    archive: HealthArchive,
    records: list[BloodPressureRecord],
) -> dict:
    sorted_records = sorted(records, key=lambda record: record.created_at)
    bmi = calculate_bmi_profile(archive.height_cm, archive.weight_jin)
    record_rows = [
        [
            item.created_at.isoformat(timespec="minutes"),
            item.systolic,
            item.diastolic,
            item.heart_rate,
            classify_pressure_detail(
                item.systolic,
                item.diastolic,
            )["status_text"],
            item.note or "",
        ]
        for item in sorted_records
    ]
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_scope": {
            "first_measurement_at": (
                sorted_records[0].created_at.isoformat(timespec="seconds")
                if sorted_records
                else None
            ),
            "last_measurement_at": (
                sorted_records[-1].created_at.isoformat(timespec="seconds")
                if sorted_records
                else None
            ),
            "record_count": len(record_rows),
            "record_days": len(
                {item.created_at.date() for item in sorted_records}
            ),
        },
        "profile": {
            "age": archive.age,
            "gender": archive.gender,
            "gender_text": (
                "男"
                if archive.gender == 1
                else "女" if archive.gender == 0 else "未填写"
            ),
            "marital_status": archive.marital_status,
            "marital_status_text": (
                "已婚"
                if archive.marital_status == 1
                else "未婚"
                if archive.marital_status == 0
                else "未填写"
            ),
            "height_cm": archive.height_cm,
            "weight_jin": archive.weight_jin,
            "bmi": bmi["value"],
            "bmi_category": bmi["category"],
            "smoking": archive.smoking,
            "smoking_text": "吸烟" if archive.smoking else "不吸烟",
            "drinking": archive.drinking,
            "drinking_text": "饮酒" if archive.drinking else "不饮酒",
            "staying_up_late": archive.staying_up_late,
            "staying_up_late_text": (
                "经常熬夜" if archive.staying_up_late else "无经常熬夜"
            ),
            "additional_notes": archive.note or "",
        },
        "blood_pressure_records": {
            "fields": [
                "measured_at",
                "systolic",
                "diastolic",
                "heart_rate",
                "classification",
                "note",
            ],
            "rows": record_rows,
        },
    }


async def generate_health_report(
    archive: HealthArchive,
    records: list[BloodPressureRecord],
    trace_id: str = "-",
) -> str:
    started_at = time.perf_counter()
    if not settings.deepseek_api_key:
        logger.warning(
            "AI health report [%s] unavailable: DeepSeek API key missing",
            trace_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=AI_REPORT_UNAVAILABLE_MESSAGE,
        )

    payload = build_health_report_payload(archive, records)
    serialized_payload = json.dumps(payload, ensure_ascii=False)
    logger.info(
        "AI health report [%s] DeepSeek request starting: "
        "model=%s records=%d record_days=%d payload_chars=%d timeout=%ss",
        trace_id,
        DEEPSEEK_HEALTH_MODEL,
        payload["data_scope"]["record_count"],
        payload["data_scope"]["record_days"],
        len(serialized_payload),
        settings.deepseek_timeout,
    )
    request_payload = {
        "model": DEEPSEEK_HEALTH_MODEL,
        "thinking": {"type": "disabled"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "以下 JSON 包含该用户在小程序使用期间的全部历史"
                    "血压、心率、每次测量备注和基础档案。请逐条分析，"
                    "生成便于医生整体、多维度掌握情况的报告：\n"
                    f"{serialized_payload}"
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 2200,
        "stream": False,
    }
    try:
        timeout = httpx.Timeout(settings.deepseek_timeout, connect=15)
        async with httpx.AsyncClient(
            timeout=timeout,
            trust_env=False,
        ) as client:
            response = await client.post(
                settings.deepseek_endpoint,
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                json=request_payload,
            )
            response.raise_for_status()
        response_payload = response.json()
        report = response_payload["choices"][0]["message"]["content"]
        if not isinstance(report, str) or not report.strip():
            raise ValueError("DeepSeek response report is empty")
        usage = response_payload.get("usage") or {}
        logger.info(
            "AI health report [%s] completed: elapsed=%.2fs "
            "report_chars=%d prompt_tokens=%s completion_tokens=%s",
            trace_id,
            time.perf_counter() - started_at,
            len(report.strip()),
            usage.get("prompt_tokens", "-"),
            usage.get("completion_tokens", "-"),
        )
        return report.strip()
    except httpx.TimeoutException as exc:
        logger.error(
            "AI health report [%s] DeepSeek timeout: elapsed=%.2fs "
            "type=%s detail=%s",
            trace_id,
            time.perf_counter() - started_at,
            type(exc).__name__,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=AI_REPORT_TIMEOUT_MESSAGE,
        ) from exc
    except httpx.ConnectError as exc:
        logger.error(
            "AI health report [%s] DeepSeek connection failed: "
            "elapsed=%.2fs detail=%s",
            trace_id,
            time.perf_counter() - started_at,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=AI_REPORT_CONNECTION_MESSAGE,
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "AI health report [%s] DeepSeek HTTP error: "
            "elapsed=%.2fs status=%s response=%s",
            trace_id,
            time.perf_counter() - started_at,
            exc.response.status_code,
            exc.response.text[:500],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=AI_REPORT_UNAVAILABLE_MESSAGE,
        ) from exc
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        logger.exception(
            "AI health report [%s] failed: elapsed=%.2fs type=%s detail=%s",
            trace_id,
            time.perf_counter() - started_at,
            type(exc).__name__,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=AI_REPORT_UNAVAILABLE_MESSAGE,
        ) from exc
