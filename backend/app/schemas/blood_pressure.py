"""血压请求和响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BloodPressureCreate(BaseModel):
    systolic: int = Field(ge=50, le=260, description="收缩压")
    diastolic: int = Field(ge=30, le=180, description="舒张压")
    heart_rate: int | None = Field(default=None, ge=30, le=220)
    measured_at: datetime | None = None
    user_id: str | None = Field(default=None, max_length=50)
    mini_user_name: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_pressure(self) -> "BloodPressureCreate":
        if self.systolic <= self.diastolic:
            raise ValueError("收缩压必须大于舒张压")
        return self


class BloodPressureUpdate(BaseModel):
    systolic: int | None = Field(default=None, ge=50, le=260)
    diastolic: int | None = Field(default=None, ge=30, le=180)
    heart_rate: int | None = Field(default=None, ge=30, le=220)
    measured_at: datetime | None = None
    note: str | None = Field(default=None, max_length=1000)


class BloodPressureOut(BaseModel):
    id: int
    systolic: int
    diastolic: int
    heart_rate: int | None
    created_at: datetime
    note: str | None
    status: str
    status_text: str

    model_config = ConfigDict(from_attributes=True)


class TrendPoint(BaseModel):
    label: str
    systolic: float | None
    diastolic: float | None
    heart_rate: float | None
    count: int


class TrendSummary(BaseModel):
    total: int
    avg_systolic: float | None
    avg_diastolic: float | None
    avg_heart_rate: float | None
    abnormal_count: int


class TrendResult(BaseModel):
    dimension: str
    start_date: datetime
    end_date: datetime
    points: list[TrendPoint]
    summary: TrendSummary

