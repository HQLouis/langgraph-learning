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
from nodes import set_background_graph, initialize_beat_manager
from ..services.output_contract_validator import validate_response_contract


class ConversationMetadata:
    """Metadata for a conversation."""

    def __init__(
        self,
        thread_id: str,
        child_id: str,
        story_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
        num_planned_tasks: Optional[int] = 5
    ):
        self.thread_id = thread_id
        self.child_id = child_id
        self.story_id = story_id
        self.chapter_id = chapter_id
        self.num_planned_tasks = num_planned_tasks
        self.created_at = datetime.utcnow()


class ConversationService:
    """Service for managing conversations with the agentic system."""

    def __init__(self, llm_model: str):
        """Initialize the conversation service."""
        load_dotenv()

        # Initialize LLM and memory
        self.llm = init_chat_model(llm_model)
        self.memory = MemorySaver()

        # Initialize beat manager for closed-world content management
        content_dir = Path(__file__).parent.parent.parent / "agentic-system" / "content"
        initialize_beat_manager(content_dir)
        print(f"✓ Beat Manager initialized with content_dir: {content_dir}")

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

    def create_conversation(
        self,
        child_id: str,
        story_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
        num_planned_tasks: Optional[int] = 5
    ) -> ConversationMetadata:
        """
        Create a new conversation.

        Args:
            child_id: ID of the child
            story_id: Optional story ID for beat-based content
            chapter_id: Optional chapter ID for beat-based content
            num_planned_tasks: Number of planned tasks for beat distribution (default: 5)

        Returns:
            ConversationMetadata with unique thread_id
        """
        # Generate unique thread ID
        session_id = str(uuid.uuid4())
        thread_id = f"conv_{session_id}"

        # Store metadata
        metadata = ConversationMetadata(
            thread_id,
            child_id,
            story_id,
            chapter_id,
            num_planned_tasks
        )
        self._conversations[thread_id] = metadata

        # Log beat system activation
        if story_id and chapter_id:
            print(f"✓ Beat system activated for {story_id}/{chapter_id} with {num_planned_tasks} tasks")
        else:
            print(f"⚠ Beat system not activated (no story_id/chapter_id), using fallback audio_book context")

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
        Send a message and stream the response with real-time formatting.
        Processes and formats chunks as they arrive for minimal latency.

        Args:
            thread_id: Thread ID of the conversation
            message: User's message

        Yields:
            Formatted chunks of the AI response as they are generated

        Raises:
            ValueError: If conversation not found
        """
        import re
        import emoji

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

        # Build initial state with beat system fields
        initial_state = {
            "messages": [user_message],
            "child_id": conversation.child_id,
        }

        # Add beat system parameters if available
        if conversation.story_id and conversation.chapter_id:
            initial_state["story_id"] = conversation.story_id
            initial_state["chapter_id"] = conversation.chapter_id
            initial_state["num_planned_tasks"] = conversation.num_planned_tasks
            print(f"✓ Using beat system: {conversation.story_id}/{conversation.chapter_id}")

        # Track streaming state
        seen_message_ids = set()
        last_chunk_content = ""

        # Stream response from immediate graph
        for event in self.immediate_graph.stream(
            initial_state,
            config,
            stream_mode="messages"
        ):
            # event is a tuple: (message, metadata)
            if isinstance(event, tuple):
                msg, metadata = event

                # Process messages from masterChatbot node (before format_response)
                node = metadata.get('langgraph_node', '')
                if node == 'masterChatbot':
                    # Skip if we've already processed this exact message
                    msg_id = getattr(msg, 'id', None)
                    if msg_id and msg_id in seen_message_ids:
                        continue

                    if hasattr(msg, 'content') and msg.content:
                        # Get only the NEW content since last chunk
                        current_content = msg.content
                        if len(current_content) > len(last_chunk_content):
                            new_chunk = current_content[len(last_chunk_content):]
                            last_chunk_content = current_content

                            # Format the chunk in real-time
                            formatted_chunk = ConversationService._format_chunk(new_chunk)

                            if formatted_chunk:
                                yield formatted_chunk

                        # Mark this message ID as seen
                        if msg_id:
                            seen_message_ids.add(msg_id)

        # Trigger background analysis asynchronously
        self._run_background_analysis(thread_id, conversation.child_id)

    @staticmethod
    def _format_chunk(chunk: str) -> str:
        """
        Format a chunk of text for TTS by removing emojis and normalizing whitespace.
        Designed to work on incremental chunks while maintaining consistency.

        Args:
            chunk: Raw text chunk from LLM

        Returns:
            Formatted chunk suitable for TTS
        """
        import re
        import emoji

        if not chunk:
            return ""

        # Find all emoji spans (handles multi-codepoint sequences, ZWJ, skin tones, etc.)
        spans = emoji.emoji_list(chunk)  # [{'emoji': '👨‍👩‍👧‍👦', 'match_start': i, 'match_end': j}, ...]

        if spans:
            # Build deletion ranges: [start_to_delete, end_of_emoji)
            # If there's a space immediately before the emoji, include it in the deletion.
            del_ranges = []
            for item in spans:
                start = item["match_start"]
                end = item["match_end"]
                # Include a single preceding space if present
                if start > 0 and chunk[start - 1] == " ":
                    start -= 1
                del_ranges.append((start, end))

            # Merge overlapping/adjacent deletion ranges to avoid index shifting issues
            del_ranges.sort()
            merged = []
            for s, e in del_ranges:
                if not merged or s > merged[-1][1]:
                    merged.append([s, e])
                else:
                    merged[-1][1] = max(merged[-1][1], e)

            # Reconstruct the string skipping the merged deletion ranges
            parts = []
            prev = 0
            for s, e in merged:
                parts.append(chunk[prev:s])
                prev = e
            parts.append(chunk[prev:])
            without_emoji = "".join(parts)
        else:
            without_emoji = chunk

        # Replace line breaks with spaces (don't strip yet)
        without_linebreaks = re.sub(r"[\r\n]+", " ", without_emoji)

        # Collapse multiple spaces to a single space
        formatted = re.sub(r" +", " ", without_linebreaks)

        return formatted

    def _run_background_analysis(self, thread_id: str, child_id: str):
        """Run background analysis in a separate thread."""
        def run_analysis():
            bg_thread_id = thread_id + "_analysis"
            print("running analysis: ", bg_thread_id)
            bg_config = {
                "configurable": {"thread_id": bg_thread_id}
            }

            # Get conversation metadata for beat system fields
            conversation = self.get_conversation(thread_id)
            bg_state = {"child_id": child_id}

            # Include beat system fields if available
            if conversation and conversation.story_id and conversation.chapter_id:
                bg_state["story_id"] = conversation.story_id
                bg_state["chapter_id"] = conversation.chapter_id
                bg_state["num_planned_tasks"] = conversation.num_planned_tasks

            try:
                self.background_graph.invoke(bg_state, bg_config)
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
                "messages": messages,
                "created_at": conversation.created_at
            }
        except Exception:
            return None
    def get_last_response_contract(self, thread_id: str, validate: bool = False) -> Optional[dict]:
        """
        Get the last response contract from the conversation state.

        Args:
            thread_id: Thread ID of the conversation
            validate: Whether to validate the contract against source content

        Returns:
            Dictionary with contract and optional validation results, or None if not found
        """
        conversation = self.get_conversation(thread_id)
        if not conversation:
            return None

        # Get state from memory
        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Get the current state
            state = self.immediate_graph.get_state(config)

            if not state or not state.values:
                return None

            response_contract = state.values.get("response_contract")
            if not response_contract:
                return {
                    "thread_id": thread_id,
                    "contract": None,
                    "message": "No response contract found (may be using legacy response format)"
                }

            result = {
                "thread_id": thread_id,
                "contract": response_contract
            }

            # Validate if requested
            if validate:
                # Get beat manager for validation (if using beat system)
                from nodes import beat_manager

                # Get story content for validation
                full_content = state.values.get("audio_book")

                validation_result = validate_response_contract(
                    response_contract,
                    beat_manager=beat_manager,
                    story_id=conversation.story_id,
                    chapter_id=conversation.chapter_id,
                    full_content=full_content
                )

                result["validation"] = validation_result.to_dict()

            return result
        except Exception as e:
            print(f"Error getting response contract: {e}")
            return None

