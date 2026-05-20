from fastapi import APIRouter
from pydantic import BaseModel

health_router = APIRouter(prefix="/health", tags=["health"])


class HealthResponseModel(BaseModel):
    status: str


@health_router.get("", response_model=HealthResponseModel, summary="Health check")
async def health():
    return {"status": "ok"}
