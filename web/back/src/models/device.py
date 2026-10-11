import uuid

from sqlalchemy import Column, DateTime, String, Float, func, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.db.postgres import Base


class Device(Base):
    """
    Модель устройства. name - идентификатор из config.json на SD-карте (device.id),
    он же второй уровень MQTT-топика: empolimer/<name>/data
    """
    __tablename__ = 'devices'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(String, nullable=True)
    location = Column(String(255), nullable=True)

    # Последнее сообщение от устройства и его последний MQTT-статус (Wi-Fi, SD, датчик, подсветка...)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    status = Column(JSONB, nullable=True)

    # Границы нормы; пусто - значения по умолчанию из настроек сервера
    temp_min = Column(Float, nullable=True)
    temp_max = Column(Float, nullable=True)
    hum_min = Column(Float, nullable=True)
    hum_max = Column(Float, nullable=True)

    data = relationship("DeviceData", back_populates="device", cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self) -> str:
        return f'<Device {self.name}>'


class DeviceData(Base):
    __tablename__ = 'device_data'
    __table_args__ = (
        # Устройство повторно отправляет очередь после обрыва связи - повторы отбрасываются.
        Index('ix_device_data_device_timestamp', 'device_id', 'timestamp', unique=True),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    battery = Column(Float, nullable=True)

    device = relationship("Device", back_populates="data")

    def __repr__(self) -> str:
        return f'<DeviceData {self.device_id} @ {self.timestamp}: {self.temperature}°C, {self.humidity}%>'
