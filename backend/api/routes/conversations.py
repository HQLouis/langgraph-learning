"""
Conversation endpoints for managing chat sessions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from backend.models.schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageRequest,
    ConversationHistory,
    ErrorResponse
)
from backend.services.conversation_service import ConversationService
from backend.api.dependencies import get_conversation_service
from typing import AsyncIterator

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Conversation created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"}
    }
)
async def create_conversation(
    request: ConversationCreate,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Create a new conversation session.

    Args:
        request: ConversationCreate with child_id and game_id
        service: Injected conversation service

    Returns:
        ConversationResponse with unique thread_id
    """
    metadata = service.create_conversation(
        child_id=request.child_id,
        game_id=request.game_id
    )

    return ConversationResponse(
        thread_id=metadata.thread_id,
        child_id=metadata.child_id,
        game_id=metadata.game_id,
        created_at=metadata.created_at
    )


@router.post(
    "/{thread_id}/messages",
    responses={
        200: {
            "description": "Message sent successfully, streaming response",
            "content": {"text/event-stream": {}}
        },
        404: {"model": ErrorResponse, "description": "Conversation not found"},
        400: {"model": ErrorResponse, "description": "Invalid message"}
    }
)
async def send_message(
    thread_id: str,
    request: MessageRequest,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Send a message to a conversation and receive streaming response via SSE.

    This endpoint uses Server-Sent Events (SSE) to stream the AI response
    in real-time as it's generated.

    Args:
        thread_id: Unique conversation thread ID
        request: MessageRequest with user's message
        service: Injected conversation service

    Returns:
        StreamingResponse with text/event-stream content type

    Raises:
        HTTPException: If conversation not found or message invalid
    """
    # Verify conversation exists
    conversation = service.get_conversation(thread_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation not found: {thread_id}"
        )

    async def event_generator() -> AsyncIterator[str]:
        """Generate SSE events from the message stream."""
        try:
            async for chunk in service.send_message_stream(thread_id, request.message):
                # Format as SSE event
                # SSE format: "data: <content>\n\n"
                yield f"data: {chunk}\n\n"

            # Send end-of-stream marker
            yield "data: [DONE]\n\n"

        except ValueError as e:
            # Conversation not found during streaming
            yield f"event: error\ndata: {str(e)}\n\n"
        except Exception as e:
            # Other errors during streaming
            yield f"event: error\ndata: Internal server error\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get(
    "/{thread_id}",
    response_model=ConversationHistory,
    responses={
        200: {"description": "Conversation history retrieved"},
        404: {"model": ErrorResponse, "description": "Conversation not found"}
    }
)
async def get_conversation_history(
    thread_id: str,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Get conversation history by thread ID.

    Args:
        thread_id: Unique conversation thread ID
        service: Injected conversation service

    Returns:
        ConversationHistory with all messages

    Raises:
        HTTPException: If conversation not found
    """
    history = service.get_conversation_history(thread_id)

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation not found: {thread_id}"
        )

    return ConversationHistory(**history)


@router.delete(
    "/{thread_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Conversation deleted successfully"},
        404: {"model": ErrorResponse, "description": "Conversation not found"}
    }
)
async def delete_conversation(
    thread_id: str,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Delete a conversation and clean up its state.

    Args:
        thread_id: Unique conversation thread ID
        service: Injected conversation service

    Raises:
        HTTPException: If conversation not found
    """
    deleted = service.delete_conversation(thread_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation not found: {thread_id}"
        )

    return None  # 204 No Content

