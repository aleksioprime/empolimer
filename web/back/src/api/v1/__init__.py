from fastapi import APIRouter
from .users import auth, ping, user
from .devices import device, data, ws

router = APIRouter()
router.include_router(ping.router, prefix="", tags=["ping"])
router.include_router(auth.router, prefix="", tags=["auth"])
router.include_router(user.router, prefix="/users", tags=["users"])
router.include_router(device.router, prefix="/devices", tags=["devices"])
router.include_router(data.router, prefix="/devices/{device_id}/data", tags=["data"])
router.include_router(ws.router, prefix="/devices", tags=["devices"])