"""
Stories endpoint for listing available story content.
"""
from fastapi import APIRouter, Depends, HTTPException
from backend.models.schemas import StoryListResponse
from backend.api.dependencies import get_beat_manager, get_conversation_service

router = APIRouter(tags=["Stories"])


@router.get(
    "/stories",
    response_model=StoryListResponse,
    responses={
        200: {"description": "Available stories and chapters"},
        503: {"description": "Beat manager not initialized"},
    },
)
async def list_stories(
    _service=Depends(get_conversation_service),
    beat_manager=Depends(get_beat_manager),
):
    """List all available stories and their chapters.

    Only includes chapters that have a beatpack file.
    """
    if beat_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Beat manager not initialized",
        )

    stories = beat_manager.list_available_stories()
    return StoryListResponse(stories=stories)
