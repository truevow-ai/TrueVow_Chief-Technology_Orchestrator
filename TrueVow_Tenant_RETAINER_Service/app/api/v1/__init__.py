from fastapi import APIRouter

from app.api.v1.routes.candidates import router as candidates_router
from app.api.v1.routes.client_api import router as client_api_router
from app.api.v1.routes.conflicts import router as conflicts_router
from app.api.v1.routes.operations import router as operations_router
from app.api.v1.routes.portal import router as portal_router
from app.api.v1.routes.signatures import router as signatures_router
from app.api.v1.routes.templates import router as templates_router
from app.api.v1.routes.v11 import router as v11_router

router = APIRouter()
router.include_router(candidates_router)
router.include_router(conflicts_router)
router.include_router(templates_router)
router.include_router(portal_router)
router.include_router(signatures_router)
router.include_router(operations_router)
router.include_router(v11_router)
router.include_router(client_api_router)


@router.get("")
async def root():
    return {"service": "retainer", "version": "0.1.0"}
