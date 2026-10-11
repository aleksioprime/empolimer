from typing import Annotated

from fastapi import Depends

from src.dependencies.uow import get_unit_of_work
from src.repositories.uow import UnitOfWork
from src.services.device import DeviceService


async def get_device_service(
        uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
):
    return DeviceService(uow=uow)