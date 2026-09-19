"""v1 API router configuration."""

from fastapi import APIRouter

from app.api.v1.cases import router as cases_router

api_router = APIRouter()
api_router.include_router(cases_router)

__all__ = ["api_router"]
