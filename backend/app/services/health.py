"""成人血压等级判定。"""

from typing import TypedDict


class PressureClassification(TypedDict):
    status: str
    status_text: str
    category: str
    hypertension_grade: int


def classify_pressure_detail(
    systolic: float, diastolic: float
) -> PressureClassification:
    """按成人诊室血压分级，收缩压与舒张压不同时取较高等级。"""
    isolated = systolic >= 140 and diastolic < 90
    if systolic >= 180 or diastolic >= 110:
        return {
            "status": "danger",
            "status_text": "高血压3级（单纯收缩期）"
            if isolated
            else "高血压3级",
            "category": "grade_3",
            "hypertension_grade": 3,
        }
    if systolic >= 160 or diastolic >= 100:
        return {
            "status": "danger",
            "status_text": "高血压2级（单纯收缩期）"
            if isolated
            else "高血压2级",
            "category": "grade_2",
            "hypertension_grade": 2,
        }
    if systolic >= 140 or diastolic >= 90:
        return {
            "status": "warning",
            "status_text": "高血压1级（单纯收缩期）"
            if isolated
            else "高血压1级",
            "category": "grade_1",
            "hypertension_grade": 1,
        }
    if systolic < 90 or diastolic < 60:
        return {
            "status": "low",
            "status_text": "血压偏低",
            "category": "low",
            "hypertension_grade": 0,
        }
    if systolic >= 120 or diastolic >= 80:
        return {
            "status": "elevated",
            "status_text": "正常高值",
            "category": "high_normal",
            "hypertension_grade": 0,
        }
    return {
        "status": "normal",
        "status_text": "正常血压",
        "category": "normal",
        "hypertension_grade": 0,
    }


def classify_pressure(systolic: float, diastolic: float) -> tuple[str, str]:
    """保留原有二元返回值，供既有调用方兼容使用。"""
    result = classify_pressure_detail(systolic, diastolic)
    return result["status"], result["status_text"]
