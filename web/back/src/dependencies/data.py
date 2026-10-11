from typing import Annotated
from datetime import datetime

from fastapi import Depends, Query

from src.schemas.data import DeviceDataQueryParams, DeviceDataPeriodParams, DeviceDataSeriesParams
from src.dependencies.uow import get_unit_of_work
from src.repositories.uow import UnitOfWork
from src.services.data import DeviceDataService


def get_device_data_params(
    limit: int = Query(50, gt=0, le=1000, description="Записей на странице"),
    offset: int = Query(0, ge=0, description="Сколько записей пропустить"),
    start: datetime | None = Query(None, description="Начальная дата/время"),
    end: datetime | None = Query(None, description="Конечная дата/время"),
) -> DeviceDataQueryParams:
    """ Query-параметры таблицы измерений """
    return DeviceDataQueryParams(limit=limit, offset=offset, start=start, end=end)


def get_device_data_period_params(
    start: datetime | None = Query(None, description="Начальная дата/время"),
    end: datetime | None = Query(None, description="Конечная дата/время"),
) -> DeviceDataPeriodParams:
    """ Query-параметры периода """
    return DeviceDataPeriodParams(start=start, end=end)


def get_device_data_series_params(
    start: datetime | None = Query(None, description="Начальная дата/время (по умолчанию - сутки назад)"),
    end: datetime | None = Query(None, description="Конечная дата/время (по умолчанию - сейчас)"),
    points: int = Query(200, ge=10, le=2000, description="Максимум точек на графике"),
) -> DeviceDataSeriesParams:
    """ Query-параметры графика """
    return DeviceDataSeriesParams(start=start, end=end, points=points)


def get_device_data_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> DeviceDataService:
    """
    Возвращает экземпляр DeviceDataService с переданным UnitOfWork (UoW)
    """
    return DeviceDataService(uow=uow)
