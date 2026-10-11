from datetime import datetime
from typing import List
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, literal_column

from src.models.device import DeviceData
from src.schemas.data import DeviceDataQueryParams, FieldStats, PeriodStats, SeriesPoint

logger = logging.getLogger(__name__)


class DeviceDataRepository:
    """
    Репозиторий измерений устройств
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _period(self, query, device_id: UUID, start: datetime | None, end: datetime | None):
        query = query.where(DeviceData.device_id == device_id)
        if start:
            query = query.where(DeviceData.timestamp >= start)
        if end:
            query = query.where(DeviceData.timestamp <= end)
        return query

    async def get_page(self, device_id: UUID, params: DeviceDataQueryParams) -> tuple[list[DeviceData], int]:
        """ Страница измерений, новые сначала, и их общее количество """
        query = self._period(select(DeviceData), device_id, params.start, params.end)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        result = await self.session.scalars(
            query.order_by(DeviceData.timestamp.desc()).limit(params.limit).offset(params.offset))
        return list(result), total or 0

    async def get_all(self, device_id: UUID, start: datetime | None, end: datetime | None) -> List[DeviceData]:
        """ Все измерения за период по возрастанию времени — для выгрузки """
        query = self._period(select(DeviceData), device_id, start, end).order_by(DeviceData.timestamp.asc())
        return list(await self.session.scalars(query))

    async def get_series(self, device_id: UUID, start: datetime, end: datetime, bucket_seconds: int) -> list[SeriesPoint]:
        """
        Точки графика: измерения группируются по отрезкам bucket_seconds (date_bin, PostgreSQL 14+),
        для каждого — среднее, минимум и максимум. Пустые отрезки не возвращаются — на графике это разрыв.
        """
        bucket = func.date_bin(
            literal_column(f"interval '{int(bucket_seconds)} seconds'"),
            DeviceData.timestamp,
            start,
        ).label("bucket")
        query = self._period(
            select(
                bucket,
                func.avg(DeviceData.temperature),
                func.min(DeviceData.temperature),
                func.max(DeviceData.temperature),
                func.avg(DeviceData.humidity),
                func.min(DeviceData.humidity),
                func.max(DeviceData.humidity),
                func.count(),
            ),
            device_id, start, end,
        ).group_by(literal_column("1")).order_by(literal_column("1"))
        # GROUP BY по номеру столбца: иначе date_bin в SELECT и GROUP BY получит разные параметры,
        # и PostgreSQL не сочтёт их одним выражением.

        rows = await self.session.execute(query)
        return [
            SeriesPoint(
                timestamp=row[0],
                temperature=_round(row[1]), temperature_min=row[2], temperature_max=row[3],
                humidity=_round(row[4]), humidity_min=row[5], humidity_max=row[6],
                count=row[7],
            )
            for row in rows
        ]

    async def get_stats(self, device_id: UUID, start: datetime | None, end: datetime | None) -> PeriodStats:
        query = self._period(
            select(
                func.count(),
                func.min(DeviceData.timestamp), func.max(DeviceData.timestamp),
                func.min(DeviceData.temperature), func.avg(DeviceData.temperature), func.max(DeviceData.temperature),
                func.min(DeviceData.humidity), func.avg(DeviceData.humidity), func.max(DeviceData.humidity),
            ),
            device_id, start, end,
        )
        row = (await self.session.execute(query)).one()
        return PeriodStats(
            count=row[0], first=row[1], last=row[2],
            temperature=FieldStats(min=row[3], avg=_round(row[4]), max=row[5]),
            humidity=FieldStats(min=row[6], avg=_round(row[7]), max=row[8]),
        )

    async def delete_by_device(self, device_id: UUID) -> int:
        """ Удаляет все измерения устройства """
        result = await self.session.execute(delete(DeviceData).where(DeviceData.device_id == device_id))
        return result.rowcount


def _round(value) -> float | None:
    return None if value is None else round(float(value), 2)
