"""
Health check endpoint.
"""
from fastapi import APIRouter
from datetime import datetime
from backend.models.schemas import HealthResponse
from backend.core.config import get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify API is running.

    Returns:
        HealthResponse with current status and timestamp
    """
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.utcnow()
    )

