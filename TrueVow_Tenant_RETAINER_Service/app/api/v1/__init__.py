from fastapi import APIRouter

from app.api.v1.routes.candidates import router as candidates_router

router = APIRouter()
router.include_router(candidates_router)


@router.get("")
async def root():
    return {"service": "retainer", "version": "0.1.0"}
