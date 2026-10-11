from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select, true
from sqlalchemy.orm import aliased
from sqlalchemy.exc import NoResultFound

from src.models.device import Device, DeviceData
from src.schemas.device import DeviceUpdateSchema


class DeviceRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    def _with_last_data(self):
        """ Устройство + его последнее измерение (LATERAL по индексу device_id, timestamp) """
        last = (
            select(DeviceData)
            .where(DeviceData.device_id == Device.id)
            .order_by(DeviceData.timestamp.desc())
            .limit(1)
            .lateral()
        )
        last_data = aliased(DeviceData, last)
        return select(Device, last_data).outerjoin(last, true())

    async def get_all(self) -> list[tuple[Device, Optional[DeviceData]]]:
        """ Все устройства с последними измерениями """
        result = await self.session.execute(self._with_last_data().order_by(Device.name))
        return [tuple(row) for row in result.all()]

    async def get_with_last_data(self, device_id: UUID) -> tuple[Optional[Device], Optional[DeviceData]]:
        result = await self.session.execute(self._with_last_data().where(Device.id == device_id))
        row = result.first()
        return (row[0], row[1]) if row else (None, None)

    async def create(self, device: Device) -> None:
        """ Создаёт новое устройство """
        self.session.add(device)
        await self.session.flush()

    async def update(self, device_id: UUID, body: DeviceUpdateSchema) -> Optional[Device]:
        """ Обновляет устройство по его ID """
        update_data = body.model_dump(exclude_unset=True)
        if not update_data:
            raise NoResultFound("Нет данных для обновления")

        await self.session.execute(update(Device).where(Device.id == device_id).values(**update_data))
        await self.session.flush()
        return await self._get_by_id(device_id)

    async def delete(self, device_id: UUID) -> None:
        """ Удаляет устройство по его ID """
        device = await self._get_by_id(device_id)
        if not device:
            raise NoResultFound(f"Устройство с ID {device_id} не найдено")
        await self.session.delete(device)

    async def _get_by_id(self, device_id: UUID) -> Optional[Device]:
        """ Получает устройство по его ID """
        result = await self.session.execute(
            select(Device).where(Device.id == device_id).execution_options(populate_existing=True))
        return result.scalars().one_or_none()
