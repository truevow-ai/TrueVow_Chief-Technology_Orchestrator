from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def root():
    return {"service": "retainer", "version": "0.1.0"}
