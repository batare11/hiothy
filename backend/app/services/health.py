"""血压状态判定。"""


def classify_pressure(systolic: float, diastolic: float) -> tuple[str, str]:
    """按家庭血压常用阈值给出展示级提示，不替代医疗诊断。"""
    if systolic >= 180 or diastolic >= 120:
        return "danger", "严重偏高"
    if systolic >= 135 or diastolic >= 85:
        return "warning", "偏高"
    if systolic < 90 or diastolic < 60:
        return "warning", "偏低"
    return "normal", "正常"

