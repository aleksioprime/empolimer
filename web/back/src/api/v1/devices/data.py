from typing import Annotated
from uuid import UUID
from urllib.parse import quote
from zoneinfo import ZoneInfo
import os

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from starlette import status

from src.schemas.security import UserJWT
from src.schemas.pagination import PaginatedResponse
from src.core.security import JWTBearer
from src.dependencies.security import role_required
from src.dependencies.data import (
    get_device_data_params, get_device_data_period_params, get_device_data_series_params, get_device_data_service,
)
from src.schemas.data import (
    DeviceDataSchema, DeviceDataQueryParams, DeviceDataPeriodParams, DeviceDataSeriesParams,
    DeviceDataSeries, DeviceDataDeleteResponse,
)
from src.services.data import DeviceDataService

router = APIRouter()


@router.get(
    path='/',
    summary='Измерения устройства постранично, новые сначала',
    response_model=PaginatedResponse[DeviceDataSchema],
    status_code=status.HTTP_200_OK,
)
async def get_device_data(
        device_id: UUID,
        params: Annotated[DeviceDataQueryParams, Depends(get_device_data_params)],
        service: Annotated[DeviceDataService, Depends(get_device_data_service)],
        user: Annotated[UserJWT, Depends(JWTBearer())],
) -> PaginatedResponse[DeviceDataSchema]:
    return await service.get_page(device_id, params)


@router.get(
    path="/series/",
    summary="График за период (среднее, минимум и максимум по отрезкам) и сводка",
    response_model=DeviceDataSeries,
    status_code=status.HTTP_200_OK,
)
async def get_device_data_series(
    device_id: UUID,
    params: Annotated[DeviceDataSeriesParams, Depends(get_device_data_series_params)],
    service: Annotated[DeviceDataService, Depends(get_device_data_service)],
    user: Annotated[UserJWT, Depends(JWTBearer())],
) -> DeviceDataSeries:
    return await service.get_series(device_id, params)


@router.delete(
    path="/",
    summary='Удалить все измерения устройства',
    response_model=DeviceDataDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_device_data(
    device_id: UUID,
    service: Annotated[DeviceDataService, Depends(get_device_data_service)],
    user: Annotated[UserJWT, Depends(role_required(admin=True, superuser=True))],
) -> DeviceDataDeleteResponse:
    return await service.delete_by_device(device_id)


@router.get(
    "/export/",
    summary="Скачать измерения за период в Excel",
    response_class=Response,
)
async def export_device_data(
    device_id: UUID,
    params: Annotated[DeviceDataPeriodParams, Depends(get_device_data_period_params)],
    service: Annotated[DeviceDataService, Depends(get_device_data_service)],
    user: Annotated[UserJWT, Depends(JWTBearer())],
):
    tz = ZoneInfo(os.environ.get("TZ") or "Europe/Moscow")
    content = await service.export_to_excel(device_id, params, tz)
    filename = "empolimer.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
