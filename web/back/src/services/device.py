from uuid import UUID
from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError, NoResultFound

from src.exceptions.base import BaseException, NotFoundException
from src.models.device import Device, DeviceData
from src.repositories.uow import UnitOfWork
from src.schemas.device import DeviceSchema, DeviceCreateSchema, DeviceUpdateSchema, DeviceEditSchema, DeviceDataSchema
from src.services import monitoring


def device_view(device: Device, last_data: Optional[DeviceData], now: Optional[datetime] = None) -> DeviceSchema:
    """ Устройство для мониторинга: последнее измерение, связь, состояние и замечания """
    online, state, problems = monitoring.evaluate(device, last_data, now)
    return DeviceSchema(
        id=device.id,
        name=device.name,
        description=device.description,
        location=device.location,
        last_seen=device.last_seen,
        status=device.status or {},
        last_data=DeviceDataSchema.model_validate(last_data) if last_data else None,
        online=online,
        state=state,
        problems=problems,
        thresholds=monitoring.thresholds(device),
        custom_thresholds=any(
            value is not None for value in (device.temp_min, device.temp_max, device.hum_min, device.hum_max)),
    )


class DeviceService:
    """
    Сервис для управления устройствами
    """
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_all(self) -> List[DeviceSchema]:
        """
        Выдаёт список всех устройств с их состоянием
        """
        async with self.uow:
            rows = await self.uow.device.get_all()

        now = datetime.now(timezone.utc)
        return [device_view(device, last_data, now) for device, last_data in rows]

    async def get_by_id(self, device_id: UUID) -> DeviceSchema:
        """
        Выдаёт устройство с состоянием по его ID
        """
        async with self.uow:
            device, last_data = await self.uow.device.get_with_last_data(device_id)

        if device is None:
            raise NotFoundException("Устройство не найдено")
        return device_view(device, last_data)

    async def create(self, body: DeviceCreateSchema) -> DeviceEditSchema:
        """
        Создаёт новое устройство
        """
        try:
            async with self.uow:
                device = Device(**body.model_dump())
                await self.uow.device.create(device)
        except IntegrityError as exc:
            raise BaseException(f"Устройство «{body.name}» уже существует") from exc

        return DeviceEditSchema.model_validate(device)

    async def update(self, device_id: UUID, body: DeviceUpdateSchema) -> DeviceEditSchema:
        """
        Обновляет информацию об устройстве по его ID
        """
        try:
            async with self.uow:
                device = await self.uow.device.update(device_id, body)
                if device is None:
                    raise NotFoundException(f"Устройство с ID {device_id} не найдено")
        except NoResultFound as exc:
            raise NotFoundException(f"Устройство с ID {device_id} не найдено") from exc
        except IntegrityError as exc:
            raise BaseException(f"Устройство «{body.name}» уже существует") from exc

        return DeviceEditSchema.model_validate(device)

    async def delete(self, device_id: UUID) -> None:
        """
        Удаляет устройство по его ID вместе с данными
        """
        try:
            async with self.uow:
                await self.uow.device.delete(device_id)
        except NoResultFound as exc:
            raise NotFoundException(f"Устройство с ID {device_id} не найдено") from exc
