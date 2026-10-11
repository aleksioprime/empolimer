from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette import status

from src.schemas.security import UserJWT
from src.core.security import JWTBearer
from src.dependencies.device import get_device_service
from src.dependencies.security import role_required
from src.schemas.device import DeviceSchema, DeviceCreateSchema, DeviceUpdateSchema, DeviceEditSchema
from src.services.device import DeviceService


router = APIRouter()
admin_required = role_required(admin=True, superuser=True)


@router.get(
    path='/',
    summary='Все устройства с последними измерениями и состоянием',
    response_model=list[DeviceSchema],
    status_code=status.HTTP_200_OK,
)
async def get_devices(
        service: Annotated[DeviceService, Depends(get_device_service)],
        user: Annotated[UserJWT, Depends(JWTBearer())],
) -> list[DeviceSchema]:
    return await service.get_all()


@router.get(
    path='/{device_id}/',
    summary='Устройство с последним измерением и состоянием',
    response_model=DeviceSchema,
    status_code=status.HTTP_200_OK,
)
async def get_device(
        device_id: UUID,
        service: Annotated[DeviceService, Depends(get_device_service)],
        user: Annotated[UserJWT, Depends(JWTBearer())],
) -> DeviceSchema:
    return await service.get_by_id(device_id)


@router.post(
    path='/',
    summary='Создаёт устройство',
    response_model=DeviceEditSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_device(
        body: DeviceCreateSchema,
        service: Annotated[DeviceService, Depends(get_device_service)],
        user: Annotated[UserJWT, Depends(admin_required)],
) -> DeviceEditSchema:
    return await service.create(body)


@router.patch(
    path='/{device_id}/',
    summary='Обновляет устройство',
    response_model=DeviceEditSchema,
    status_code=status.HTTP_200_OK,
)
async def update_device(
        device_id: UUID,
        body: DeviceUpdateSchema,
        service: Annotated[DeviceService, Depends(get_device_service)],
        user: Annotated[UserJWT, Depends(admin_required)],
) -> DeviceEditSchema:
    return await service.update(device_id, body)


@router.delete(
    path='/{device_id}/',
    summary='Удаляет устройство вместе с измерениями',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_device(
        device_id: UUID,
        service: Annotated[DeviceService, Depends(get_device_service)],
        user: Annotated[UserJWT, Depends(admin_required)],
) -> None:
    await service.delete(device_id)
