from fastapi import APIRouter
from .reports import router as reports_router
from .coordinator import router as coordinator_router
from .sms import router as sms_router
from .teams import router as teams_router
from .auth_routes import router as auth_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(reports_router)
api_router.include_router(coordinator_router)
api_router.include_router(sms_router)
api_router.include_router(teams_router)
api_router.include_router(auth_router)

# Also expose a router without /v1 prefix for /api compatibility
api_legacy_router = APIRouter(prefix="/api")
api_legacy_router.include_router(reports_router)
api_legacy_router.include_router(coordinator_router)
api_legacy_router.include_router(sms_router)
api_legacy_router.include_router(teams_router)
api_legacy_router.include_router(auth_router)



