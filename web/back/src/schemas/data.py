from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.device import DeviceDataSchema  # noqa: F401 — общая схема измерения


class DeviceDataQueryParams(BaseModel):
    limit: int = Field(50, gt=0, le=1000)
    offset: int = Field(0, ge=0, description="Сколько записей пропустить")
    start: Optional[datetime] = Field(None, description="Начальная дата/время")
    end: Optional[datetime] = Field(None, description="Конечная дата/время")


class DeviceDataPeriodParams(BaseModel):
    start: Optional[datetime] = Field(None, description="Начальная дата/время (по умолчанию — сутки назад)")
    end: Optional[datetime] = Field(None, description="Конечная дата/время (по умолчанию — сейчас)")


class DeviceDataSeriesParams(DeviceDataPeriodParams):
    points: int = Field(200, ge=10, le=2000, description="Сколько точек на графике (не больше)")


class SeriesPoint(BaseModel):
    """Среднее, минимум и максимум за отрезок графика."""

    timestamp: datetime
    temperature: Optional[float] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    humidity: Optional[float] = None
    humidity_min: Optional[float] = None
    humidity_max: Optional[float] = None
    count: int


class FieldStats(BaseModel):
    min: Optional[float] = None
    avg: Optional[float] = None
    max: Optional[float] = None


class PeriodStats(BaseModel):
    count: int = 0
    first: Optional[datetime] = None
    last: Optional[datetime] = None
    temperature: FieldStats = FieldStats()
    humidity: FieldStats = FieldStats()


class DeviceDataSeries(BaseModel):
    start: datetime
    end: datetime
    bucket_seconds: int = Field(..., description="Длина отрезка, за который усреднена точка")
    points: list[SeriesPoint]
    stats: PeriodStats


class DeviceDataDeleteResponse(BaseModel):
    device_id: UUID = Field(..., description="ID устройства")
    deleted_count: int = Field(..., description="Кол-во удалённых данных")
