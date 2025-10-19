"""
Dependency injection for FastAPI routes.
"""
from functools import lru_cache
from backend.services.conversation_service import ConversationService
from backend.core.config import get_settings


@lru_cache()
def get_conversation_service() -> ConversationService:
    """
    Get or create a singleton conversation service.

    This is cached to ensure we use the same service instance
    across all requests, maintaining conversation state.
    """
    settings = get_settings()
    return ConversationService(llm_model=settings.llm_model)

