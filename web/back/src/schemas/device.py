from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Как device.id в config.json прошивки
DEVICE_NAME_PATTERN = r"^[A-Za-z0-9_-]{1,32}$"


class DeviceDataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="ID полученных данных")
    timestamp: datetime = Field(..., description="Дата/время измерения")
    temperature: Optional[float] = Field(None, description="Температура воздуха, °C")
    humidity: Optional[float] = Field(None, description="Влажность воздуха, %")
    battery: Optional[float] = Field(None, description="Напряжение батареи, В")


class Thresholds(BaseModel):
    temp_min: float
    temp_max: float
    hum_min: float
    hum_max: float


class DeviceProblem(BaseModel):
    code: str = Field(..., description="Код: offline, sensor, sd, temp_high...")
    level: Literal["info", "warning", "error"]
    text: str


class DeviceSchema(BaseModel):
    id: UUID = Field(..., description="Уникальный идентификатор устройства")
    name: str = Field(..., description="Идентификатор устройства из config.json (device.id)")
    description: Optional[str] = Field(None, description="Описание устройства")
    location: Optional[str] = Field(None, description="Местоположение устройства")
    last_seen: Optional[datetime] = Field(None, description="Последнее сообщение от устройства")
    status: dict = Field(default_factory=dict, description="Последнее состояние, присланное устройством")
    last_data: Optional[DeviceDataSchema] = Field(None, description="Последнее измерение")
    online: bool = False
    state: Literal["new", "offline", "warning", "ok"] = "new"
    problems: list[DeviceProblem] = Field(default_factory=list)
    thresholds: Thresholds
    custom_thresholds: bool = Field(False, description="Границы нормы заданы для устройства, а не по умолчанию")


class DeviceEditSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    hum_min: Optional[float] = None
    hum_max: Optional[float] = None


class DeviceCreateSchema(BaseModel):
    name: str = Field(..., pattern=DEVICE_NAME_PATTERN, description="device.id из config.json")
    description: Optional[str] = Field(None, max_length=1000)
    location: Optional[str] = Field(None, max_length=255)
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    hum_min: Optional[float] = None
    hum_max: Optional[float] = None


class DeviceUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, pattern=DEVICE_NAME_PATTERN)
    description: Optional[str] = Field(None, max_length=1000)
    location: Optional[str] = Field(None, max_length=255)
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    hum_min: Optional[float] = None
    hum_max: Optional[float] = None
