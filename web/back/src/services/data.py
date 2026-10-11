from uuid import UUID
from io import BytesIO
from datetime import datetime, timedelta, timezone
import logging

from openpyxl import Workbook
from openpyxl.styles import Font

from src.exceptions.base import BaseException
from src.schemas.pagination import PaginatedResponse
from src.schemas.data import (
    DeviceDataSchema, DeviceDataQueryParams, DeviceDataPeriodParams, DeviceDataSeriesParams,
    DeviceDataSeries, DeviceDataDeleteResponse,
)
from src.repositories.uow import UnitOfWork

logger = logging.getLogger(__name__)

# Отрезки графика округляются до «понятных» значений: 1, 5, 15 минут, час...
BUCKETS = [60, 120, 300, 600, 900, 1800, 3600, 7200, 10800, 21600, 43200, 86400]


def bucket_for(start: datetime, end: datetime, points: int) -> int:
    seconds = max((end - start).total_seconds() / points, 60)
    return next((bucket for bucket in BUCKETS if bucket >= seconds), BUCKETS[-1])


def resolve_period(params: DeviceDataPeriodParams) -> tuple[datetime, datetime]:
    end = params.end or datetime.now(timezone.utc)
    start = params.start or end - timedelta(days=1)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if start >= end:
        raise BaseException("Начало периода должно быть раньше конца")
    return start, end


class DeviceDataService:
    """ Сервис для работы с измерениями устройства """
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_page(self, device_id: UUID, params: DeviceDataQueryParams) -> PaginatedResponse[DeviceDataSchema]:
        """
        Страница измерений устройства, новые сначала
        """
        async with self.uow:
            items, total = await self.uow.data.get_page(device_id, params)

        return PaginatedResponse[DeviceDataSchema](
            items=[DeviceDataSchema.model_validate(item) for item in items],
            total=total,
            limit=params.limit,
            offset=params.offset,
            has_next=params.offset + params.limit < total,
            has_previous=params.offset > 0,
        )

    async def get_series(self, device_id: UUID, params: DeviceDataSeriesParams) -> DeviceDataSeries:
        """
        График за период: не больше params.points точек (усреднение по отрезкам) и сводка min/avg/max
        """
        start, end = resolve_period(params)
        bucket = bucket_for(start, end, params.points)
        async with self.uow:
            points = await self.uow.data.get_series(device_id, start, end, bucket)
            stats = await self.uow.data.get_stats(device_id, start, end)
        return DeviceDataSeries(start=start, end=end, bucket_seconds=bucket, points=points, stats=stats)

    async def delete_by_device(self, device_id: UUID) -> DeviceDataDeleteResponse:
        """
        Удаляет все измерения устройства
        """
        async with self.uow:
            deleted_count = await self.uow.data.delete_by_device(device_id)
        return DeviceDataDeleteResponse(device_id=device_id, deleted_count=deleted_count)

    async def export_to_excel(self, device_id: UUID, params: DeviceDataPeriodParams, tz: timezone) -> bytes:
        """
        Формирует файл Excel с измерениями за период (без периода - все)
        """
        async with self.uow:
            rows = await self.uow.data.get_all(device_id, params.start, params.end)

        wb = Workbook()
        ws = wb.active
        ws.title = "Измерения"
        ws.append(["Дата и время", "Температура, °C", "Влажность, %", "Батарея, В"])
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for row in rows:
            ws.append([
                row.timestamp.astimezone(tz).replace(tzinfo=None),
                row.temperature,
                row.humidity,
                row.battery,
            ])
        ws.column_dimensions["A"].width = 20
        for column in "BCD":
            ws.column_dimensions[column].width = 16
        for cell in ws["A"][1:]:
            cell.number_format = "dd.mm.yyyy hh:mm:ss"
        ws.freeze_panes = "A2"

        output = BytesIO()
        wb.save(output)
        return output.getvalue()
