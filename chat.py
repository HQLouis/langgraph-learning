#!/usr/bin/env python3
"""
Interactive chat application for Lingolino with streaming responses.
Run this file to start an interactive chat session.
"""
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

from immediate_graph import create_immediate_response_graph
from background_graph import create_background_analysis_graph
from nodes import set_background_graph
from immediate_graph import set_config

import threading


def start_chat():
    """Initialize and start the interactive chat session."""
    # Load environment variables
    load_dotenv()

    # Initialize LLM and memory
    print("🚀 Initializing Lingolino chat system...", flush=True)
    llm = init_chat_model("google_genai:gemini-2.0-flash")
    memory = MemorySaver()

    # Create the graphs
    background_graph = create_background_analysis_graph(llm, memory)
    set_background_graph(background_graph)
    immediate_graph = create_immediate_response_graph(llm, memory, background_graph)

    print("✅ System ready!\n", flush=True)

    # Get child and game IDs
    print("👋 Welcome to Lingolino!\n")
    child_id = input("Enter Child ID (1-3, default=1): ").strip() or "1"
    game_id = input("Enter Game ID (0, default=0): ").strip() or "0"

    # Create unique thread ID for this session
    import uuid
    session_id = str(uuid.uuid4())[:8]
    thread_id = f"session_{session_id}"

    config = {
        "configurable": {"thread_id": thread_id}
    }
    set_config(config)

    print(f"\n🎮 Session started (ID: {session_id})")
    print("💡 Type 'quit' or 'exit' to end the conversation\n")
    print("="*60)

    # Chat loop
    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Goodbye! Thanks for chatting with Lingolino!")
                break

            # Add user message to state
            user_message = HumanMessage(content=user_input)

            print("\n🤖 Lino: ", end="", flush=True)

            # Track messages we've seen to avoid duplicates
            seen_message_ids = set()

            # Stream through the immediate graph with messages mode for token-by-token streaming
            for event in immediate_graph.stream(
                {"messages": [user_message]},
                config,
                stream_mode="messages"
            ):
                # event is a tuple: (message, metadata)
                if isinstance(event, tuple):
                    message, metadata = event

                    # Skip if we've already seen this message
                    if hasattr(message, 'id') and message.id in seen_message_ids:
                        continue

                    # Only process AI messages from format_response node
                    # metadata contains 'langgraph_node' showing which node emitted it
                    if (hasattr(message, 'type') and
                        message.type == 'ai' and
                        metadata.get('langgraph_node') == 'format_response'):

                        if hasattr(message, 'content') and message.content:
                            print(message.content, end="", flush=True)

                            # Mark this message as seen
                            if hasattr(message, 'id'):
                                seen_message_ids.add(message.id)

            print()  # New line after complete message

            # Trigger background analysis asynchronously (non-blocking)
            # Use threading to truly run in background without waiting
            def run_background_analysis():
                bg_thread_id = thread_id + "_analysis"
                bg_config = {
                    "configurable": {"thread_id": bg_thread_id}
                }
                try:
                    # Invoke the background graph (don't need to consume stream)
                    background_graph.invoke(
                        {"child_id": child_id, "game_id": game_id},
                        bg_config
                    )
                except Exception:
                    pass  # Suppress background errors for better UX

            # Start background analysis in separate thread (fire-and-forget)
            analysis_thread = threading.Thread(target=run_background_analysis, daemon=True)
            analysis_thread.start()

        except KeyboardInterrupt:
            print("\n\n👋 Chat interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print("Let's try again...")


if __name__ == "__main__":
    start_chat()
