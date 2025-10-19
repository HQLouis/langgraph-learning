"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""
    child_id: str = Field(..., description="ID of the child (1-3)")
    game_id: str = Field(..., description="ID of the game (e.g., 0)")

    class Config:
        json_schema_extra = {
            "example": {
                "child_id": "1",
                "game_id": "0"
            }
        }


class ConversationResponse(BaseModel):
    """Schema for conversation creation response."""
    thread_id: str = Field(..., description="Unique thread ID for this conversation")
    child_id: str
    game_id: str
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "conv_abc123def456",
                "child_id": "1",
                "game_id": "0",
                "created_at": "2025-10-20T10:30:00Z"
            }
        }


class MessageRequest(BaseModel):
    """Schema for sending a message."""
    message: str = Field(..., min_length=1, description="User's message content")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hello! Can you tell me a story?"
            }
        }


class MessageInHistory(BaseModel):
    """Schema for a single message in conversation history."""
    role: str = Field(..., description="Message role (human/ai)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None


class ConversationHistory(BaseModel):
    """Schema for conversation history response."""
    thread_id: str
    child_id: str
    game_id: str
    messages: list[MessageInHistory]
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "conv_abc123",
                "child_id": "1",
                "game_id": "0",
                "messages": [
                    {"role": "human", "content": "Hello!"},
                    {"role": "ai", "content": "Hi there! How can I help you?"}
                ],
                "created_at": "2025-10-20T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str
    error_code: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Conversation not found",
                "error_code": "CONVERSATION_NOT_FOUND"
            }
        }


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    app_name: str
    version: str
    timestamp: datetime

