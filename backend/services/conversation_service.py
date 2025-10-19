"""
Service layer for conversation management and interaction with agentic system.
"""
import uuid
import threading
from datetime import datetime
from typing import Optional, AsyncIterator
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

import sys
from pathlib import Path

# Add agentic-system to path
agentic_path = Path(__file__).parent.parent.parent / "agentic-system"
sys.path.insert(0, str(agentic_path))

from immediate_graph import create_immediate_response_graph, set_config
from background_graph import create_background_analysis_graph
from nodes import set_background_graph


class ConversationMetadata:
    """Metadata for a conversation."""

    def __init__(self, thread_id: str, child_id: str, game_id: str):
        self.thread_id = thread_id
        self.child_id = child_id
        self.game_id = game_id
        self.created_at = datetime.utcnow()


class ConversationService:
    """Service for managing conversations with the agentic system."""

    def __init__(self, llm_model: str):
        """Initialize the conversation service."""
        load_dotenv()

        # Initialize LLM and memory
        self.llm = init_chat_model(llm_model)
        self.memory = MemorySaver()

        # Create graphs
        self.background_graph = create_background_analysis_graph(self.llm, self.memory)
        set_background_graph(self.background_graph)
        self.immediate_graph = create_immediate_response_graph(
            self.llm,
            self.memory,
            self.background_graph
        )

        # In-memory storage for conversation metadata
        # Key: thread_id, Value: ConversationMetadata
        self._conversations: dict[str, ConversationMetadata] = {}

    def create_conversation(self, child_id: str, game_id: str) -> ConversationMetadata:
        """
        Create a new conversation.

        Args:
            child_id: ID of the child
            game_id: ID of the game

        Returns:
            ConversationMetadata with unique thread_id
        """
        # Generate unique thread ID
        session_id = str(uuid.uuid4())
        thread_id = f"conv_{session_id}"

        # Store metadata
        metadata = ConversationMetadata(thread_id, child_id, game_id)
        self._conversations[thread_id] = metadata

        return metadata

    def get_conversation(self, thread_id: str) -> Optional[ConversationMetadata]:
        """Get conversation metadata by thread ID."""
        return self._conversations.get(thread_id)

    def delete_conversation(self, thread_id: str) -> bool:
        """
        Delete a conversation and clean up its state.

        Args:
            thread_id: Thread ID to delete

        Returns:
            True if deleted, False if not found
        """
        if thread_id not in self._conversations:
            return False

        # Remove from conversations dict
        del self._conversations[thread_id]

        # TODO: Clean up from MemorySaver when LangGraph provides deletion API
        # For now, MemorySaver doesn't have a built-in delete method
        # The state will remain in memory but won't be accessible via API

        return True

    async def send_message_stream(
        self,
        thread_id: str,
        message: str
    ) -> AsyncIterator[str]:
        """
        Send a message and stream the response.

        Args:
            thread_id: Thread ID of the conversation
            message: User's message

        Yields:
            Chunks of the AI response as they are generated

        Raises:
            ValueError: If conversation not found
        """
        # Verify conversation exists
        conversation = self.get_conversation(thread_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {thread_id}")

        # Create config
        config = {
            "configurable": {"thread_id": thread_id}
        }
        set_config(config)

        # Create user message
        user_message = HumanMessage(content=message)

        # Track streaming state
        seen_message_ids = set()
        seen_content = ""

        # Stream response from immediate graph
        for event in self.immediate_graph.stream(
            {"messages": [user_message]},
            config,
            stream_mode="messages"
        ):
            # event is a tuple: (message, metadata)
            if isinstance(event, tuple):
                msg, metadata = event

                # Only process messages from format_response node
                node = metadata.get('langgraph_node', '')
                if node == 'format_response':
                    # Skip if we've already processed this exact message
                    msg_id = getattr(msg, 'id', None)
                    if msg_id and msg_id in seen_message_ids:
                        continue

                    if hasattr(msg, 'content') and msg.content:
                        # Yield only the NEW content
                        if len(msg.content) > len(seen_content):
                            new_content = msg.content[len(seen_content):]
                            seen_content = msg.content
                            yield new_content

                        # Mark this message ID as seen
                        if msg_id:
                            seen_message_ids.add(msg_id)

        # Trigger background analysis asynchronously
        self._run_background_analysis(thread_id, conversation.child_id, conversation.game_id)

    def _run_background_analysis(self, thread_id: str, child_id: str, game_id: str):
        """Run background analysis in a separate thread."""
        def run_analysis():
            bg_thread_id = thread_id + "_analysis"
            bg_config = {
                "configurable": {"thread_id": bg_thread_id}
            }
            try:
                self.background_graph.invoke(
                    {"child_id": child_id, "game_id": game_id},
                    bg_config
                )
            except Exception:
                # Suppress background errors
                pass

        # Start background analysis in separate thread (fire-and-forget)
        analysis_thread = threading.Thread(target=run_analysis, daemon=True)
        analysis_thread.start()

    def get_conversation_history(self, thread_id: str) -> Optional[dict]:
        """
        Get conversation history.

        Args:
            thread_id: Thread ID of the conversation

        Returns:
            Dictionary with conversation history or None if not found
        """
        conversation = self.get_conversation(thread_id)
        if not conversation:
            return None

        # Get state from memory
        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Get the current state
            state = self.immediate_graph.get_state(config)

            messages = []
            if state and state.values and "messages" in state.values:
                for msg in state.values["messages"]:
                    role = "human" if msg.__class__.__name__ == "HumanMessage" else "ai"
                    messages.append({
                        "role": role,
                        "content": msg.content,
                        "timestamp": None  # MemorySaver doesn't store timestamps
                    })

            return {
                "thread_id": thread_id,
                "child_id": conversation.child_id,
                "game_id": conversation.game_id,
                "messages": messages,
                "created_at": conversation.created_at
            }
        except Exception:
            return None

