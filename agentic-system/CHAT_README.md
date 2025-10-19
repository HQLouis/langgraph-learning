# Interactive Chat Application

This document explains how to use the new interactive chat application for Lingolino.

## Overview

The `chat.py` file provides an interactive command-line chat interface that:
- **Streams responses** from the LLM in real-time (token-by-token) via LangGraph's streaming
- Uses the **immediate_graph** for user-facing responses with full orchestration logic
- Runs the **background_graph** asynchronously for analysis (non-blocking)
- Maintains conversation history and context
- Supports child profiles and different game modes

## Architecture

### Key Design Principle: Graph-Only Orchestration

**All LLM calls happen exclusively within graph nodes.** The `chat.py` file only:
- Collects user input
- Passes messages to the graph
- Displays streamed responses from the graph
- Does NOT call the LLM directly

This ensures:
- ✅ All business logic stays in the graph
- ✅ Easy to modify conversation flow by editing nodes
- ✅ Proper state management through LangGraph
- ✅ Streaming works through graph's built-in capabilities

### How Streaming Works

1. **User Input**: `chat.py` creates a `HumanMessage` from user input
2. **Graph Execution**: Passes message to `immediate_graph.stream()` with `stream_mode="messages"`
3. **Node Processing**: Nodes call `llm.stream()` internally
4. **LangGraph Streaming**: LangGraph captures streaming chunks from nodes
5. **Display**: `chat.py` receives chunks and displays them in real-time
6. **State Update**: Graph automatically updates state with final response

### Graph Flow

**Immediate Graph:**
```
START → initialStateLoader? → load_analysis → masterChatbot → format_response → END
```

**Background Graph (async):**
```
START → initialStateLoader? → [educationalWorker, storytellingWorker] → END
```

## Key Features

### 1. Real-Time Streaming Responses
The chat application uses LangGraph's `stream_mode="messages"` to capture and display LLM tokens as they are generated within the `masterChatbot` and `format_response` nodes.

### 2. Dual Graph Architecture
- **Immediate Graph**: Handles direct user interactions with streaming responses
- **Background Graph**: Analyzes conversations asynchronously without blocking the chat
  - Educational analysis
  - Storytelling suggestions

### 3. Memory Persistence
Each session maintains conversation history, allowing the AI to reference previous messages.

## How to Start

### Quick Start
```bash
python chat.py
```

Or make it executable and run directly:
```bash
chmod +x chat.py
./chat.py
```

### Interactive Setup
When you start the application, you'll be prompted for:
1. **Child ID** (1-3, default=1): Selects the child profile
   - Child 1: 5 years old, likes dinosaurs and rockets
   - Child 2: 8 years old, likes football and video games
   - Child 3: 10 years old, likes programming and robotics

2. **Game ID** (0, default=0): Selects the game mode
   - Game 0: Lino the explaining teddy bear

### During Chat
- Type your messages and press Enter
- Responses stream in real-time
- Type `quit`, `exit`, or `bye` to end the conversation
- Press Ctrl+C to interrupt at any time

## Example Session

```
🚀 Initializing Lingolino chat system...
✅ System ready!

👋 Welcome to Lingolino!

Enter Child ID (1-3, default=1): 1
Enter Game ID (0, default=0): 0

🎮 Session started (ID: a1b2c3d4)
💡 Type 'quit' or 'exit' to end the conversation

============================================================

👤 You: Why is the sky blue?

🤖 Lino: Das ist eine tolle Frage! Die Luft über uns ist eigentlich durchsichtig, 
aber sie besteht aus vielen kleinen Teilchen. Wenn das Licht von der Sonne kommt...
```

## Implementation Details

### Nodes with Streaming

Both `masterChatbot` and `format_response` nodes use `llm.stream()`:

```python
def masterChatbot(state: State, llm):
    # ... prepare messages ...
    response_content = ""
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'content'):
            response_content += chunk.content
    return {"messages": [AIMessage(content=response_content)]}
```

### Chat Display

The `chat.py` uses `stream_mode="messages"` to capture streaming:

```python
for event in immediate_graph.stream(
    {"messages": [user_message]},
    config,
    stream_mode="messages"
):
    # Display streaming chunks from nodes
    if isinstance(event, tuple):
        message, metadata = event
        if hasattr(message, 'content') and message.content:
            print(message.content, end="", flush=True)
```

### Background Analysis
The background graph runs asynchronously without blocking user interaction:
- Analyzes conversation context
- Updates educational insights
- Suggests story developments
- Results are available for the next interaction via `load_analysis` node

## Differences from Notebook

| Aspect | Notebook (`lingolino.ipynb`) | Chat App (`chat.py`) |
|--------|------------------------------|---------------------|
| Interface | Jupyter cells | Command-line interactive |
| Responses | Complete at once | Streamed in real-time |
| Execution | Manual cell execution | Continuous loop |
| State | Visible in variables | Managed by graphs |
| Background | Visible execution | Silent/non-blocking |
| Orchestration | Mixed (notebook + graphs) | 100% in graphs |
| Portability | Requires Jupyter | Standalone Python script |

## Technical Details

### State Management
The application maintains state through:
- Thread IDs for session isolation
- Memory checkpointer for persistence
- Separate analysis thread for background processing

### Error Handling
- Background errors are suppressed to avoid interrupting chat
- Main errors are displayed with traceback
- Keyboard interrupts gracefully exit

### Configuration
The session configuration is set globally using `set_config()` to ensure all graph components use the same thread context.

## Files Structure

- **`chat.py`**: Main interactive application (UI only, no LLM calls)
- **`nodes.py`**: All node functions with LLM logic and streaming
- **`immediate_graph.py`**: Immediate response graph definition
- **`background_graph.py`**: Background analysis graph definition
- **`states.py`**: State type definitions
- **`data_loaders.py`**: Helper functions for loading profiles

## Future Enhancements

Potential improvements (marked with TODO in code):
- Conditional analysis execution (e.g., every 3rd message)
- Timeout handling for slow analysis
- Better visual indicators for background processing
- Save/load conversation sessions
- Multi-modal support (voice input/output)

## Troubleshooting

### No streaming visible
- Check your terminal supports ANSI output
- Ensure flush=True is working in your environment
- Verify nodes are using `llm.stream()` not `llm.invoke()`

### Background errors
- Background analysis errors are suppressed by default
- Check the graph state if analysis results seem missing

### Import errors
- Ensure all dependencies are installed
- Run from the project root directory
- Check that `.env` file exists with API keys
