import uuid

from sqlalchemy import Column, DateTime, String, Float, func, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.db.postgres import Base

# Копия нужных воркеру столбцов из web/back/src/models/device.py; схему меняют миграции бэкенда.


class Device(Base):
    __tablename__ = 'devices'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(255), unique=True, nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    status = Column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f'<Device {self.name}>'


class DeviceData(Base):
    __tablename__ = 'device_data'
    __table_args__ = (
        Index('ix_device_data_device_timestamp', 'device_id', 'timestamp', unique=True),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    battery = Column(Float, nullable=True)
